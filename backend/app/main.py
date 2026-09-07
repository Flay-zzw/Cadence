import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4
from urllib.parse import urlparse
from dotenv import load_dotenv, set_key
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from . import storage, llm
from .models import Generate, Settings, Edit, Regenerate
from .demo import demo_content

load_dotenv(storage.ROOT / '.env')
@asynccontextmanager
async def lifespan(app):
    recover_jobs()
    yield


app = FastAPI(title='Cadence Studio', version='0.1.0', lifespan=lifespan)
locks: dict[str, asyncio.Lock] = {}
templates = Environment(loader=FileSystemLoader(storage.ROOT / 'app' / 'templates'), autoescape=select_autoescape())


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Never echo request values, which may contain an API key.
    return JSONResponse(status_code=422, content={'detail': '输入格式不正确，请检查字段内容和长度。'})


@app.middleware('http')
async def local_only(request: Request, call_next):
    if request.headers.get('host', '').split(':')[0] not in ('127.0.0.1', 'localhost', 'testserver'):
        return Response('Local access only', status_code=403)
    origin = request.headers.get('origin')
    if origin and origin not in ('http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:8000', 'http://127.0.0.1:8000'):
        return Response('Origin not allowed', status_code=403)
    return await call_next(request)


def settings():
    path = storage.DATA / 'settings.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'base_url': os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'), 'model': os.getenv('OPENAI_MODEL', '')}


def configured():
    load_dotenv(storage.ROOT / '.env', override=True)
    value = settings()
    if not os.getenv('OPENAI_API_KEY') or not value['model']:
        raise HTTPException(400, '请在模型设置中填写 API Key 和模型名。')
    return value


def persist(content, model, pace=180, aspect_ratio='16:9'):
    if aspect_ratio == '9:16':
        for page in content.pages:
            page.narration = ''
    value = {'id': str(uuid4()), 'revision': 1, 'created_at': datetime.now(timezone.utc).isoformat(), 'pace': pace,
             'aspect_ratio': aspect_ratio, 'content': content.model_dump(), 'generation_meta': {'model': model, 'prompt_version': 'v2'}}
    storage.write(storage.project_path(value['id']), value)
    return value


@app.get('/api/health')
def health(): return {'status': 'ok'}


@app.get('/api/settings/model')
def get_settings():
    load_dotenv(storage.ROOT / '.env', override=True)
    return {**settings(), 'key_configured': bool(os.getenv('OPENAI_API_KEY'))}


def validate_base_url(base_url):
    parsed = urlparse(base_url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(422, '请输入有效的不含凭证的 HTTP(S) Base URL')


@app.put('/api/settings/model')
def put_settings(value: Settings):
    validate_base_url(value.base_url)
    key = value.api_key.get_secret_value().strip() if value.api_key else ''
    if '\n' in key or '\r' in key:
        raise HTTPException(422, 'API Key 不能包含换行。')
    if key:
        set_key(str(storage.ROOT / '.env'), 'OPENAI_API_KEY', key)
    storage.write(storage.DATA / 'settings.json', value.model_dump(exclude={'api_key'}))
    return get_settings()


@app.post('/api/settings/model/test')
async def test_model_settings(value: Settings):
    validate_base_url(value.base_url)
    load_dotenv(storage.ROOT / '.env', override=True)
    key = value.api_key.get_secret_value().strip() if value.api_key else os.getenv('OPENAI_API_KEY', '').strip()
    if not key:
        raise HTTPException(400, '请先填写 API Key。')
    if not value.model:
        raise HTTPException(400, '请先填写模型名称。')
    try:
        return await llm.test_connection(value.base_url, value.model, key)
    except Exception as exc:
        raise HTTPException(400, llm.connection_error(exc)) from exc


async def run_generation(identifier, request, config):
    path = storage.DATA / 'jobs' / (identifier + '.json')
    job = {'id': identifier, 'status': 'running', 'message': '正在准备'}
    audit = []
    def update(message):
        job['message'] = message
        storage.write(path, job)
    try:
        content = await llm.generate_content(request, config, update, audit)
        for i, page in enumerate(content.pages): page.id = f'page-{i+1:02}'
        project = persist(content, config['model'], request.pace, request.aspect_ratio)
        job.update(status='completed', message='生成完成', project_id=project['id'])
    except Exception as exc:
        job.update(status='failed', message=llm.friendly_error(exc))
        storage.write(storage.DATA / 'diagnostics' / (identifier + '.json'), {'error_type': type(exc).__name__, 'outputs': audit})
    storage.write(path, job)


@app.post('/api/generations', status_code=202)
async def create_generation(value: Generate, tasks: BackgroundTasks):
    config = configured()
    identifier = str(uuid4())
    job = {'id': identifier, 'status': 'queued', 'message': '已加入生成队列'}
    storage.write(storage.DATA / 'jobs' / (identifier + '.json'), job)
    tasks.add_task(run_generation, identifier, value, config)
    return job


@app.get('/api/generations/{identifier}')
def get_generation(identifier: str):
    name = storage.project_path(identifier).name
    path = storage.DATA / 'jobs' / name
    if not path.exists(): raise HTTPException(404, '任务不存在')
    return json.loads(path.read_text(encoding='utf-8'))


def recover_jobs():
    for path in (storage.DATA / 'jobs').glob('*.json'):
        job = json.loads(path.read_text(encoding='utf-8'))
        if job['status'] in ('queued', 'running'):
            job.update(status='failed', message='服务已重启，请重新提交生成。')
            storage.write(path, job)


@app.post('/api/projects/demo')
def demo(): return persist(demo_content(), 'demo')


@app.get('/api/projects')
def list_projects():
    values = [json.loads(p.read_text(encoding='utf-8')) for p in (storage.DATA / 'projects').glob('*.json')]
    return [{'id': v['id'], 'title': v['content']['title'], 'created_at': v['created_at']} for v in sorted(values, key=lambda v: v['created_at'], reverse=True)]


@app.get('/api/projects/{identifier}')
def get_project(identifier: str): return storage.read_project(identifier)


def find_page(project, page_id):
    for i, page in enumerate(project['content']['pages']):
        if page['id'] == page_id: return i
    raise HTTPException(404, '页面不存在')


@app.patch('/api/projects/{identifier}/pages/{page_id}')
async def edit_page(identifier: str, page_id: str, value: Edit):
    async with locks.setdefault(identifier, asyncio.Lock()):
        project = storage.read_project(identifier)
        if project['revision'] != value.revision: raise HTTPException(409, '项目已更新，请重新打开项目后编辑。')
        i = find_page(project, page_id)
        if value.page.id != page_id: raise HTTPException(422, '页面 ID 不可修改')
        if project.get('aspect_ratio') == '9:16':
            value.page.narration = ''
        project['content']['pages'][i] = value.page.model_dump()
        project['revision'] += 1
        storage.write(storage.project_path(identifier), project)
        return project


@app.post('/api/projects/{identifier}/pages/{page_id}/regenerate')
async def regenerate(identifier: str, page_id: str, value: Regenerate):
    config = configured()
    project = storage.read_project(identifier)
    i = find_page(project, page_id)
    if project['revision'] != value.revision: raise HTTPException(409, '项目已更新，请重新打开项目。')
    audit = []
    try:
        page = await llm.regenerate_page(project, project['content']['pages'][i], value.instruction, config, audit)
    except Exception as exc:
        storage.write(storage.DATA / 'diagnostics' / (str(uuid4()) + '.json'), {'error_type': type(exc).__name__, 'outputs': audit})
        raise HTTPException(502, llm.friendly_error(exc))
    page.id = page_id
    return await edit_page(identifier, page_id, Edit(page=page, revision=value.revision))


@app.get('/api/projects/{identifier}/export/{kind}')
def export(identifier: str, kind: str):
    project = storage.read_project(identifier)
    content = project['content']
    if kind == 'html':
        result = templates.get_template('deck.html').render(project=project, css=(storage.ROOT / 'app/templates/deck.css').read_text(encoding='utf-8'))
        return HTMLResponse(result, headers={'Content-Disposition': 'attachment; filename="cadence.html"'})
    if kind == 'script':
        if project.get('aspect_ratio') == '9:16':
            raise HTTPException(400, '图文模式无需口播稿。')
        result = '# ' + content['title'] + '\n\n' + '\n\n'.join(f'## {i+1}. {p["title"]}\n\n{p["narration"]}' for i,p in enumerate(content['pages']))
        return Response(result, media_type='text/markdown', headers={'Content-Disposition': 'attachment; filename="narration.md"'})
    if kind == 'json':
        return Response(json.dumps(project, ensure_ascii=False, indent=2), media_type='application/json', headers={'Content-Disposition': 'attachment; filename="project.json"'})
    raise HTTPException(404, '不支持的导出格式')
