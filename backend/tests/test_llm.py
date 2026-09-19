import asyncio
from types import SimpleNamespace
from app.llm import structured
from app.models import Content
from app.demo import demo_content
from app.models import Generate, Outline
from app import llm
import pytest


class FakeStream:
    def __init__(self, raw, fail=False):
        self.raw, self.fail, self.closed = raw, fail, False
    async def __aenter__(self): return self
    async def __aexit__(self, *args): self.closed = True
    async def __aiter__(self):
        import httpx
        for part in [self.raw[:10], self.raw[10:]]:
            yield SimpleNamespace(choices=[SimpleNamespace(index=0, finish_reason=None, delta=SimpleNamespace(content=part, refusal=None))])
            if self.fail: raise httpx.ReadError('connection dropped')
        yield SimpleNamespace(choices=[SimpleNamespace(index=0, finish_reason='stop', delta=SimpleNamespace(content=None, refusal=None))])


def test_invalid_json_is_repaired_once():
    class Completions:
        calls = 0
        async def create(self, **kwargs):
            self.calls += 1
            raw = 'invalid json' if self.calls == 1 else demo_content().model_dump_json()
            assert kwargs['stream'] is True
            return FakeStream(raw)
    completions = Completions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    audit = []
    result = asyncio.run(structured(client,'test',Content,'generate',audit))
    assert len(result.pages) == 4
    assert completions.calls == 2
    assert audit[0] == 'invalid json'


def test_portrait_accepts_empty_narration():
    content = demo_content()
    for page in content.pages:
        page.narration = ''
    class Completions:
        async def create(self, **kwargs):
            return FakeStream(content.model_dump_json())
    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    result = asyncio.run(structured(client, 'test', Content, '图文', [], '9:16'))
    assert all(page.narration == '' for page in result.pages)


@pytest.mark.parametrize('ratio', ['9:16', '16:9'])
def test_generation_plans_then_emits_real_page_boundaries(monkeypatch, ratio):
    content = demo_content()
    outline = Outline(**content.model_dump(exclude={'pages', 'style'}),
                      pages=[dict(role=p.role, title=p.title, brief=p.body) for p in content.pages])
    events = []
    class Client:
        def __init__(self, **kwargs):
            assert kwargs['timeout'].read == 600
            assert kwargs['timeout'].connect == 20
            assert kwargs['max_retries'] == 0
            self.chat = SimpleNamespace(completions=self)
            self.page_calls = 0
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def create(self, **kwargs):
            if kwargs['response_format']['json_schema']['name'] == 'Outline':
                raw = outline.model_dump_json()
            else:
                # Fail the first page once to exercise visible repair without advancing progress.
                self.page_calls += 1
                raw = 'invalid' if self.page_calls == 1 else content.pages[self.page_calls-2].model_dump_json()
            return FakeStream(raw)
    monkeypatch.setattr(llm, 'AsyncOpenAI', Client)
    result = asyncio.run(llm.generate_content(
        Generate(article='测试科普素材。'*30, aspect_ratio=ratio), {'model':'test','base_url':'http://test'},
        lambda message, **data: events.append(data), []))
    assert len(result.pages) == 4
    assert [e['page_index'] for e in events if 'page_index' in e] == [1, 2, 3, 4]
    assert len([e for e in events if 'completed_page' in e]) == 4
    assert any(e.get('attempt') == 2 for e in events)
    assert next(e['planned_pages'] for e in events if 'planned_pages' in e)[0]['title'] == content.pages[0].title
    assert events[-1]['stage'] == 'validating'
    assert all(bool(p.narration) == (ratio == '16:9') for p in result.pages)


def test_model_clients_allow_slow_responses_without_hidden_network_retries(monkeypatch):
    captured = []
    class Client:
        def __init__(self, **kwargs):
            captured.append(kwargs)
            self.chat = SimpleNamespace(completions=self)
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def create(self, **kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='连接成功'))])
    monkeypatch.setattr(llm, 'AsyncOpenAI', Client)
    async def result(*args, **kwargs): return demo_content().pages[0]
    monkeypatch.setattr(llm, 'structured', result)
    asyncio.run(llm.test_connection('http://test', 'test', 'test-key'))
    asyncio.run(llm.regenerate_page({'content': {}}, {}, '重写', {'base_url':'http://test','model':'test'}, []))
    assert captured[0]['timeout'].read == 90
    assert captured[1]['timeout'].read == 600
    assert all(c['timeout'].connect == 20 and c['max_retries'] == 0 for c in captured)


def test_stream_disconnect_retries_only_current_request_and_discards_partial():
    streams, events = [], []
    class Completions:
        async def create(self, **kwargs):
            stream = FakeStream(demo_content().model_dump_json(), fail=not streams)
            streams.append(stream)
            return stream
    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    audit = []
    result = asyncio.run(structured(client, 'test', Content, 'generate', audit, on_transport=events.append))
    assert len(result.pages) == 4
    assert len(streams) == 2 and all(s.closed for s in streams)
    assert len(audit) == 1
    assert sum('1/1' in e for e in events) == 1


def test_stream_retry_is_bounded_and_never_accepts_partial_json():
    import httpx
    streams = []
    class Completions:
        async def create(self, **kwargs):
            stream = FakeStream(demo_content().model_dump_json(), fail=True)
            streams.append(stream)
            return stream
    audit = []
    with pytest.raises(httpx.ReadError):
        asyncio.run(structured(SimpleNamespace(chat=SimpleNamespace(completions=Completions())), 'test', Content, 'generate', audit))
    assert len(streams) == 2
    assert all(s.closed for s in streams)
    assert audit == []


def test_diagnostics_do_not_include_exception_messages_or_credentials():
    import httpx
    cause = httpx.ReadError('secret-key and private article')
    error = llm.APIConnectionError(request=httpx.Request('POST','https://example.com'))
    error.__cause__ = cause
    result = llm.error_diagnostics(error)
    assert result['causes'] == [{'type':'APIConnectionError'}, {'type':'ReadError'}]
    assert 'secret-key' not in str(result)
    assert '途中' in llm.friendly_error(error)


def test_stream_missing_completion_marker_is_not_accepted():
    import httpx
    calls = []
    class Incomplete(FakeStream):
        async def __aiter__(self):
            yield SimpleNamespace(choices=[SimpleNamespace(index=0, finish_reason=None, delta=SimpleNamespace(content=self.raw, refusal=None))])
    class Completions:
        async def create(self, **kwargs):
            stream = Incomplete(demo_content().model_dump_json())
            calls.append(stream)
            return stream
    with pytest.raises(httpx.RemoteProtocolError):
        asyncio.run(structured(SimpleNamespace(chat=SimpleNamespace(completions=Completions())), 'test', Content, 'generate', []))
    assert len(calls) == 2


def test_authentication_failure_is_not_retried():
    import httpx
    calls = []
    class Completions:
        async def create(self, **kwargs):
            calls.append(kwargs)
            raise llm.AuthenticationError('invalid key', response=httpx.Response(401,request=httpx.Request('POST','https://example.com')), body=None)
    with pytest.raises(llm.AuthenticationError):
        asyncio.run(structured(SimpleNamespace(chat=SimpleNamespace(completions=Completions())), 'test', Content, 'generate', []))
    assert len(calls) == 1


def test_stream_deadline_closes_a_stalled_response(monkeypatch):
    class Stalled(FakeStream):
        async def __aiter__(self):
            await asyncio.sleep(1)
            yield SimpleNamespace(choices=[])
    stream = Stalled('')
    class Completions:
        async def create(self, **kwargs): return stream
    monkeypatch.setattr(llm, 'REQUEST_DEADLINE_SECONDS', 0.01)
    with pytest.raises(TimeoutError):
        asyncio.run(structured(SimpleNamespace(chat=SimpleNamespace(completions=Completions())), 'test', Content, 'generate', []))
    assert stream.closed


def test_model_proxy_can_be_disabled_without_changing_system(monkeypatch):
    captured = {}
    transport = object()
    def http_client(**kwargs):
        captured.update(kwargs)
        return transport
    monkeypatch.setattr(llm, 'DefaultAsyncHttpxClient', http_client)
    monkeypatch.setattr(llm, 'AsyncOpenAI', lambda **kwargs: kwargs)
    monkeypatch.setenv('CADENCE_USE_SYSTEM_PROXY', 'false')
    assert llm.model_client(api_key='test')['http_client'] is transport
    assert captured == {'trust_env': False}
    monkeypatch.setenv('CADENCE_USE_SYSTEM_PROXY', 'true')
    assert 'http_client' not in llm.model_client(api_key='test')


def test_network_permission_failure_is_actionable_and_not_retried():
    import httpx
    error = llm.APIConnectionError(request=httpx.Request('POST', 'https://example.com'))
    error.__cause__ = PermissionError(13, 'private credential')
    calls = []
    class Completions:
        async def create(self, **kwargs):
            calls.append(kwargs)
            raise error
    assert '联网权限被拒绝' in llm.connection_error(error)
    assert 'private credential' not in llm.connection_error(error)
    with pytest.raises(llm.APIConnectionError):
        asyncio.run(llm.structured(SimpleNamespace(chat=SimpleNamespace(completions=Completions())),
                                  'test', Content, 'generate', []))
    assert len(calls) == 1


def test_connection_test_reports_tls_disconnect():
    import ssl
    import httpx
    error = llm.APIConnectionError(request=httpx.Request('POST', 'https://example.com'))
    error.__cause__ = ssl.SSLEOFError(8, 'private upstream message')
    assert 'TLS' in llm.connection_error(error)
