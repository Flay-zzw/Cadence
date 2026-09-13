"""Shared presentation rules for offline exports; mirrored in Slide.tsx."""
import json
import re
from pathlib import Path

ICONS = json.loads((Path(__file__).parent/'templates/slide-icons.json').read_text(encoding='utf-8'))
ROLES = dict(cover='开篇', hook='看见问题', concept='核心概念', explain='原理拆解', example='场景应用', myth='认知纠偏', summary='重点回顾', cta='行动指南')
ROLE_ICONS = dict(cover='spark', hook='bulb', concept='bulb', explain='layers', example='target', myth='target', summary='check', cta='arrow')


def paragraphs(text):
    result = []
    for block in re.split(r'\n+', text):
        if not block.strip(): continue
        buffer = ''
        for sentence in re.findall(r'[^。！？!?]+[。！？!?]*|[。！？!?]+', block):
            buffer += sentence
            if len(buffer) >= 45:
                result.append(buffer)
                buffer = ''
        if buffer: result.append(buffer)
    return result


def point_parts(text):
    clean = re.sub(r'^[\s,，]*(?:[•·\-]|[（(]?\d+[）).、．])\s*', '', text)
    match = re.search('[：:]', clean)
    if match and 0 < match.start() <= 12:
        return dict(title=clean[:match.start()], detail=clean[match.end():].strip())
    return dict(title=clean, detail='')
