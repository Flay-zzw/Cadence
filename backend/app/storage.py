import json
import os
from pathlib import Path
from uuid import UUID, uuid4
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv('CADENCE_DATA_DIR', str(ROOT / 'data')))


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.' + uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def project_path(identifier):
    try:
        identifier = str(UUID(identifier))
    except ValueError:
        raise HTTPException(404, '项目不存在')
    return DATA / 'projects' / (identifier + '.json')


def read_project(identifier):
    path = project_path(identifier)
    if not path.exists():
        raise HTTPException(404, '项目不存在')
    return json.loads(path.read_text(encoding='utf-8'))
