import asyncio
from types import SimpleNamespace
from app.llm import structured
from app.models import Content
from app.demo import demo_content


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
