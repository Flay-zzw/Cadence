from app.content_quality import has_placeholder, validate_page_content
from app.presentation import semantic_icon, visible_points
from app.demo import demo_content
import pytest


def test_legacy_placeholder_filter_keeps_real_content_and_literal_mentions():
    assert visible_points(['>{短标题：具体说明}>', '沙箱：隔离执行环境']) == ['沙箱：隔离执行环境']
    assert not has_placeholder('给文章起一个短标题，可以帮助读者快速理解。')
    assert not has_placeholder('记住进度：中断后继续任务')


def test_duplicate_highlights_require_repair():
    page = demo_content().pages[0]
    page.highlights = ['散射改变方向', '散射改变方向。']
    with pytest.raises(ValueError, match='重复'):
        validate_page_content(page)


def test_content_specific_icons():
    assert semantic_icon('AI不只是聊天') == 'bot'
    assert semantic_icon('沙箱：隔离执行环境') == 'shield'
    assert semantic_icon('记住进度：中断后继续任务') == 'memory'
    assert semantic_icon('工具：连接外部服务') == 'tool'
    assert semantic_icon('未匹配内容', 'target') == 'target'
