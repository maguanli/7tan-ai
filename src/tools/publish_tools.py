"""
发布工具 — 7坛管理后台自动发布
"""
import time
import json
import random

from loguru import logger
from .registry import register_tool


@register_tool(
    name="publish_to_7tan",
    description="在7坛管理后台发布资源。自动填写表单、上传 LOGO/截图、提交发布。",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "发布标题"},
            "intro": {"type": "string", "description": "简介/正文内容"},
            "category": {"type": "string", "description": "分类"},
            "tags": {"type": "string", "description": "标签（逗号分隔）"},
            "download_url": {"type": "string", "description": "下载链接（OSS 外链）"},
            "logo_path": {"type": "string", "description": "本地 LOGO 路径"},
            "screenshot_paths": {"type": "string", "description": "本地截图路径（JSON 数组）"},
            "resource_type": {"type": "string", "description": "'game' 或 'software'", "default": "game"},
        },
        "required": ["title", "intro", "download_url"]
    },
    category="publish",
    requires_browser=True,
    dangerous=True,
)
def publish_to_7tan(title: str, intro: str, download_url: str, category: str = "",
                    tags: str = "", logo_path: str = "", screenshot_paths: str = "",
                    resource_type: str = "game") -> str:
    """
    自动发布到7坛后台。
    使用 BrowserBridge 线程安全操作浏览器，通过 CSS 选择器填写表单。
    AI 在调用前应先用 browse_page 了解7坛后台的发帖表单结构。
    """
    import time as _time
    from .browser_bridge import get_bridge
    from .browser_tools import login_7tan, browse_page, click_element
    from ..config.loader import load_config

    config = load_config()
    bridge = get_bridge()
    if bridge is None:
        return "❌ 浏览器未启动，请先打开浏览器页面"

    try:
        # 确保登录
        login_result = login_7tan(
            config.get("site_7tan", {}).get("username", ""),
            config.get("site_7tan", {}).get("password", "")
        )

        # 访问管理后台发布页
        admin_url = config.get("site_7tan", {}).get("base_url", "https://img.7tan.cn")
        bridge.navigate(f"{admin_url}/admin", wait_seconds=5.0)

        # 查找并点击"发布"或"新增"按钮
        publish_btn_selectors = [
            'a:has-text("发布")', 'a:has-text("新增")', 'a:has-text("添加")',
            'button:has-text("发布")', 'button:has-text("新增")',
            '.publish-btn', '#publish-btn',
        ]

        clicked = False
        for sel in publish_btn_selectors:
            try:
                bridge.click(sel)
                _time.sleep(3)
                clicked = True
                logger.info(f"✅ 点击了发布按钮: {sel}")
                break
            except Exception:
                continue

        if not clicked:
            bridge.navigate(f"{admin_url}/admin/post.php?action=new", wait_seconds=5.0)

        _time.sleep(2)

        # 填写表单（用 Bridge 执行 JS 填充）
        _fill_form_via_bridge(bridge, title, intro, category, tags, download_url,
                              logo_path, screenshot_paths, resource_type)

        # 随机延迟
        delay = random.uniform(
            config.get("site_7tan", {}).get("publish_delay_min", 30),
            config.get("site_7tan", {}).get("publish_delay_max", 120),
        )
        logger.info(f"⏳ 随机延迟 {delay:.0f} 秒后提交...")
        _time.sleep(min(delay, 5))

        # 提交
        submit_selectors = [
            'button[type="submit"]', 'button:has-text("提交")',
            'button:has-text("发布")', 'input[type="submit"]',
            '.submit-btn', '#submit-btn',
        ]
        for sel in submit_selectors:
            try:
                bridge.click(sel)
                _time.sleep(3)
                break
            except Exception:
                continue

        _time.sleep(3)

        # 验证结果
        current_title = bridge.get_page_title()
        page_text = bridge.get_page_text(500)
        if "成功" in page_text or "success" in current_title.lower():
            logger.info(f"✅ 发布成功: {title}")
            return f"✅ 发布成功!\n  标题: {title}"
        else:
            return f"⚠️ 发布已提交，请手动验证。标题: {title}"

    except Exception as e:
        logger.error(f"❌ 发布失败: {e}")
        return f"❌ 发布失败: {e}"


def _fill_form_via_bridge(bridge, title, intro, category, tags, download_url,
                          logo_path, screenshot_paths, resource_type):
    """通过 Bridge 执行 JS 填写发布表单"""
    # 标题
    for sel in ['input[name="title"]', '#title', 'input[placeholder*="标题"]', '.title-input input']:
        bridge.execute_js(f"""
            (function() {{
                var el = document.querySelector('{sel}');
                if (el) {{ el.value = {json.dumps(title)}; el.dispatchEvent(new Event('input')); return 'ok'; }}
                return 'not found';
            }})()
        """, timeout=2.0)

    # 分类
    if category:
        for sel in ['select[name="category"]', '#category', 'select[name="type"]']:
            bridge.execute_js(f"""
                (function() {{
                    var el = document.querySelector('{sel}');
                    if (el) {{ el.value = '{category}'; el.dispatchEvent(new Event('change')); return 'ok'; }}
                    return 'not found';
                }})()
            """, timeout=2.0)

    # 内容
    intro_selectors = [
        'textarea[name="content"]', 'textarea[name="intro"]', '#content',
        '.editor textarea', '.ck-content', '[contenteditable="true"]',
    ]
    for sel in intro_selectors:
        escaped_intro = json.dumps(intro)
        bridge.execute_js(f"""
            (function() {{
                var el = document.querySelector('{sel}');
                if (el) {{
                    if (el.isContentEditable) el.innerHTML = {escaped_intro};
                    else el.value = {escaped_intro};
                    el.dispatchEvent(new Event('input'));
                    return 'ok';
                }}
                return 'not found';
            }})()
        """, timeout=2.0)

    # 下载链接
    if download_url:
        for sel in ['input[name="download_url"]', 'input[name="download"]',
                     '#download_url', 'input[placeholder*="下载"]']:
            bridge.execute_js(f"""
                (function() {{
                    var el = document.querySelector('{sel}');
                    if (el) {{ el.value = '{download_url}'; el.dispatchEvent(new Event('input')); return 'ok'; }}
                    return 'not found';
                }})()
            """, timeout=2.0)

    # 标签
    if tags:
        for sel in ['input[name="tags"]', '#tags', 'input[placeholder*="标签"]']:
            bridge.execute_js(f"""
                (function() {{
                    var el = document.querySelector('{sel}');
                    if (el) {{ el.value = '{tags}'; el.dispatchEvent(new Event('input')); return 'ok'; }}
                    return 'not found';
                }})()
            """, timeout=2.0)
