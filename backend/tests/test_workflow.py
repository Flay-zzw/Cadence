import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import storage, llm
from app.demo import demo_content


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DATA', tmp_path)
    with TestClient(app) as c:
        yield c


def test_edit_export_and_conflict(client):
    project = client.post('/api/projects/demo').json()
    page = project['content']['pages'][0]
    page['title'] = '<script>alert(1)</script>'
    url = f'/api/projects/{project["id"]}/pages/{page["id"]}'
    edited = client.patch(url, json={'page': page, 'revision': 1})
    assert edited.status_code == 200
    assert edited.json()['revision'] == 2
    assert client.patch(url, json={'page':page,'revision':1}).status_code == 409
    html = client.get(f'/api/projects/{project["id"]}/export/html').text
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html
    assert 'https://' not in html
    assert client.get(f'/api/projects/{project["id"]}/export/script').status_code == 200
    assert client.get(f'/api/projects/{project["id"]}/export/json').json()['revision'] == 2
    assert len(client.get('/api/projects').json()) == 1
    assert client.get('/api/projects/not-an-id').status_code == 404


def test_generation_success_and_failure(client, monkeypatch):
    monkeypatch.setattr('app.main.configured', lambda: {'model':'test','base_url':'https://api.openai.com/v1'})
    async def generate(*args): return demo_content()
    monkeypatch.setattr(llm, 'generate_content', generate)
    job = client.post('/api/generations', json={'article':'有效的测试素材。'*30}).json()
    result = client.get('/api/generations/'+job['id']).json()
    assert result['status'] == 'completed'
    assert client.get('/api/projects/'+result['project_id']).status_code == 200
    async def fail(*args): raise ValueError('invalid output')
    monkeypatch.setattr(llm, 'generate_content', fail)
    job = client.post('/api/generations', json={'article':'有效的测试素材。'*30}).json()
    assert client.get('/api/generations/'+job['id']).json()['status'] == 'failed'
    assert client.post('/api/generations', json={'article':'太短'}).status_code == 422


def test_settings_and_origin(client):
    assert 'api_key' not in client.get('/api/settings/model').json()
    assert client.put('/api/settings/model',json={'model':'test','base_url':'https://user:secret@example.com'}).status_code == 422
    assert client.put('/api/settings/model',json={'model':'test','base_url':'https://api.openai.com/v1'}).status_code == 200
    assert client.post('/api/projects/demo',headers={'origin':'https://untrusted.example'}).status_code == 403
    assert client.get('/api/health',headers={'host':'untrusted.example'}).status_code == 403


@pytest.mark.parametrize('ratio', ['9:16', '16:9'])
def test_format_persists_and_controls_exports(client, monkeypatch, ratio):
    monkeypatch.setattr('app.main.configured', lambda: {'model': 'test'})
    async def generate(*args):
        return demo_content()
    monkeypatch.setattr(llm, 'generate_content', generate)
    job = client.post('/api/generations', json={'article': '彩虹来自光在水滴中的折射。'*20, 'aspect_ratio': ratio}).json()
    result = client.get('/api/generations/'+job['id']).json()
    project = client.get('/api/projects/'+result['project_id']).json()
    assert project['aspect_ratio'] == ratio
    assert all(bool(p['narration']) == (ratio == '16:9') for p in project['content']['pages'])
    prefix = '/api/projects/'+project['id']
    assert client.get(prefix+'/export/script').status_code == (200 if ratio == '16:9' else 400)
    html = client.get(prefix+'/export/html').text
    assert ('slide portrait' if ratio == '9:16' else 'slide landscape') in html
    assert 'SCIENCE NOTES' not in html
    page = project['content']['pages'][0]
    page['narration'] = '编辑时尝试写入口播'
    edited = client.patch(prefix+'/pages/'+page['id'], json={'page': page, 'revision': 1}).json()
    assert edited['content']['pages'][0]['narration'] == ('' if ratio == '9:16' else page['narration'])


def test_invalid_format(client):
    assert client.post('/api/generations', json={'article': '科普素材。'*30, 'aspect_ratio': '1:1'}).status_code == 422


def test_model_connection_without_saving(client, monkeypatch):
    captured = {}
    async def connect(base_url, model, api_key):
        captured.update(base_url=base_url, model=model, api_key=api_key)
        return {'ok': True, 'message': '连接成功，API Key 和模型均可用。'}
    monkeypatch.setattr(llm, 'test_connection', connect)
    response = client.post('/api/settings/model/test', json={
        'base_url': 'https://example.com/v1', 'model': 'test-model', 'api_key': 'test-key'
    })
    assert response.status_code == 200
    assert response.json()['ok'] is True
    assert captured == {'base_url': 'https://example.com/v1', 'model': 'test-model', 'api_key': 'test-key'}
    assert not (storage.DATA/'settings.json').exists()


def test_regenerate_conflict(client, monkeypatch):
    monkeypatch.setattr('app.main.configured', lambda: {'model':'test','base_url':'https://api.openai.com/v1'})
    project = client.post('/api/projects/demo').json()
    async def regenerate(*args):
        current = storage.read_project(project['id'])
        current['revision'] += 1
        storage.write(storage.project_path(project['id']),current)
        return demo_content().pages[0]
    monkeypatch.setattr(llm, 'regenerate_page', regenerate)
    result = client.post(f'/api/projects/{project["id"]}/pages/page-01/regenerate',json={'instruction':'解释得更清楚','revision':1})
    assert result.status_code == 409


def test_interrupted_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DATA',tmp_path)
    path=tmp_path/'jobs'/'sample.json'
    storage.write(path, {'id':'sample','status':'running'})
    with TestClient(app): pass
    assert json.loads(path.read_text(encoding='utf-8'))['status']=='failed'


def test_key_write_only_and_preserved(client, tmp_path, monkeypatch):
    import os
    from dotenv import dotenv_values
    monkeypatch.setattr(storage, 'ROOT', tmp_path)
    monkeypatch.setenv('OPENAI_API_KEY', '')
    secret = 'test-only-key-not-a-real-credential'
    payload = {'model': 'test', 'base_url': 'https://api.openai.com/v1', 'api_key': secret}
    response = client.put('/api/settings/model', json=payload)
    assert response.status_code == 200
    assert response.json()['key_configured'] is True
    assert secret not in response.text
    assert secret not in client.get('/api/settings/model').text
    assert secret not in (storage.DATA/'settings.json').read_text()
    assert dotenv_values(tmp_path/'.env')['OPENAI_API_KEY'] == secret
    payload['api_key'] = ''
    assert client.put('/api/settings/model', json=payload).status_code == 200
    assert dotenv_values(tmp_path/'.env')['OPENAI_API_KEY'] == secret
    payload['api_key'] = 'test-replacement'
    assert client.put('/api/settings/model', json=payload).status_code == 200
    assert os.environ['OPENAI_API_KEY'] == 'test-replacement'
    payload['api_key'] = {'secret': secret}
    invalid = client.put('/api/settings/model', json=payload)
    assert invalid.status_code == 422
    assert secret not in invalid.text
