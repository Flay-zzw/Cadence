"""Reject template scaffolding without inventing replacement facts."""
import re

PLACEHOLDERS = {
    '短标题', '小标题', '要点标题', '具体说明', '具体内容', '示例标题',
    '填写标题', '填写内容', '待补充', '待填写', '标题', '说明',
    '短标题具体说明', '小标题具体说明',
}


def has_placeholder(text):
    # Includes malformed wrappers seen in model output: >{短标题：具体说明}>.
    for part in re.split(r'[：:\n]', text):
        compact = re.sub(r'[\s{}<>《》【】\[\]（）()*_`#>，,。.!！?？、/\\-]', '', part)
        if compact in PLACEHOLDERS:
            return True
    return False


def validate_page_content(page):
    if any(has_placeholder(text) for text in [page.title, page.body, *page.highlights]):
        raise ValueError('页面含格式占位词。请从原文提炼真实观点，重写标题、正文和重点；不要照抄字段说明。')
    normalized = [re.sub(r'\W', '', text) for text in page.highlights]
    if len(set(normalized)) != len(normalized):
        raise ValueError('重点内容重复，请保留不同的真实信息。')
