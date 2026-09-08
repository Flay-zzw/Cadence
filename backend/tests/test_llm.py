import asyncio
from types import SimpleNamespace
from app.llm import structured
from app.models import Content
from app.demo import demo_content
from app.models import Generate, Outline
from app import llm
import pytest


def test_invalid_json_is_repaired_once():
    class Completions:
        calls = 0
        async def create(self, **kwargs):
            self.calls += 1
            raw = 'invalid json' if self.calls == 1 else demo_content().model_dump_json()
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content=raw,refusal=None))])
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
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content=content.model_dump_json(), refusal=None))])
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
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content=raw, refusal=None))])
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
