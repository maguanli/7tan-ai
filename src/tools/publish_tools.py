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
    智能导航：登录 → 读取页面链接 → 找到「安卓游戏」→ 找到「发布」按钮 → 填写表单 → 提交。
    使用 BrowserBridge 线程安全操作浏览器。
    """
    from .browser_bridge import get_bridge
    from .browser_tools import login_7tan
    from ..config.loader import load_config

    config = load_config()
    bridge = get_bridge()
    if bridge is None:
        return "❌ 浏览器未启动，请先打开浏览器页面"

    try:
        admin_url = config.get("site_7tan", {}).get("base_url", "https://img.7tan.cn")
        steps = []

        # 切换到管理后台上下文（先确保窗口已打开）
        from .browser_tools import set_active_context, _admin_view
        set_active_context("admin")
        if _admin_view is None:
            steps.append("⚠️ 请先在浏览器页面点击「打开管理后台」按钮，或手动在浏览器新标签中打开管理后台")
        else:
            steps.append("🔧 管理后台窗口已就绪")
        # ===== 步骤 1: 登录 =====
        login_result = login_7tan(
            config.get("site_7tan", {}).get("username", ""),
            config.get("site_7tan", {}).get("password", "")
        )
        steps.append(f"🔐 登录: {login_result[:80]}")

        # ===== 步骤 2: 浏览管理后台首页，读取所有链接 =====
        bridge.navigate(f"{admin_url}/admin", wait_seconds=5.0)
        time.sleep(2)
        
        all_links = bridge.get_page_links(100)  # 读取最多 100 个链接
        page_text = bridge.get_page_text(8000)   # 读取更多文本
        page_title = bridge.get_page_title()
        steps.append(f"📄 进入后台: {page_title} ({len(all_links)}个链接)")
        
        # ===== 步骤 3: 在链接和文本中搜索「安卓游戏」入口 =====
        android_link = None
        android_keywords = ["安卓游戏", "安卓", "Android", "android", "手游", "发布安卓"]
        
        # 3a: 首先在链接文本中搜索
        for link in all_links:
            link_text = link.get("text", "")
            link_href = link.get("href", "")
            for kw in android_keywords:
                if kw.lower() in link_text.lower() or kw.lower() in link_href.lower():
                    android_link = link
                    break
            if android_link:
                break
        
        # 3b: 如果链接没找到，在页面文本中搜索「安卓游戏」附近的链接
        if not android_link:
            for kw in android_keywords:
                if kw in page_text:
                    # 找到了文本中有「安卓游戏」，尝试用选择器点击
                    nav_selectors = [
                        f'a:has-text("{kw}")',
                        f'li:has-text("{kw}") a',
                        f'.sidebar a:has-text("{kw}")',
                        f'.nav a:has-text("{kw}")',
                        f'[class*="menu"] a:has-text("{kw}")',
                        f'[class*="nav"] a:has-text("{kw}")',
                    ]
                    for sel in nav_selectors:
                        result = bridge.click(sel)
                        if "not_found" not in result and "超时" not in result:
                            android_link = {"text": kw, "href": sel, "clicked": True}
                            steps.append(f"🔗 通过文本匹配点击了「{kw}」")
                            break
                    if android_link:
                        break
        
        # 3c: 如果还没找到，输出所有链接让 AI 判断
        if not android_link:
            links_summary = "\n".join([
                f"  [{i}] {l.get('text','(空)')[:60]} → {l.get('href','')[:80]}"
                for i, l in enumerate(all_links[:50])
            ])
            steps.append(f"⚠️ 未找到「安卓游戏」入口，页面链接如下:\n{links_summary}")
            return "❌ 未找到「安卓游戏」入口。" + "\n".join(steps) + \
                   "\n\n💡 建议：先用 browse_page 仔细查看后台页面结构，告诉我「安卓游戏」的链接文字或 URL。"
        
        # ===== 步骤 4: 点击「安卓游戏」进入列表页 =====
        if not android_link.get("clicked"):
            href = android_link.get("href", "")
            text = android_link.get("text", "")
            steps.append(f"🔗 找到入口: 「{text}」→ {href}")
            
            # 如果是相对路径或完整 URL
            if href.startswith("http"):
                bridge.navigate(href, wait_seconds=4.0)
            elif href.startswith("/") or href.startswith("?"):
                bridge.navigate(f"{admin_url}{href}", wait_seconds=4.0)
            elif href:
                bridge.navigate(f"{admin_url}/admin/{href}", wait_seconds=4.0)
            else:
                # 用选择器点击
                click_result = bridge.click(f'a:has-text("{text}")')
                steps.append(f"   点击结果: {click_result}")
        
        time.sleep(3)
        
        # ===== 步骤 5: 在安卓游戏页面找「发布」按钮 =====
        android_page_text = bridge.get_page_text(5000)
        android_page_links = bridge.get_page_links(60)
        android_page_title = bridge.get_page_title()
        steps.append(f"📱 安卓游戏页面: {android_page_title}")
        
        # 搜索「发布」相关按钮
        publish_keywords = ["发布安卓", "发布游戏", "发布", "新增", "添加游戏", "添加"]
        clicked_publish = False
        
        for kw in publish_keywords:
            publish_selectors = [
                f'a:has-text("{kw}")',
                f'button:has-text("{kw}")',
                f'span:has-text("{kw}")',
                f'.btn:has-text("{kw}")',
                f'[class*="btn"]:has-text("{kw}")',
            ]
            for sel in publish_selectors:
                result = bridge.click(sel)
                if "not_found" not in result and "超时" not in result:
                    steps.append(f"✅ 点击发布按钮: {result}")
                    clicked_publish = True
                    break
            if clicked_publish:
                break
        
        # 也尝试在链接列表中找发布入口
        if not clicked_publish:
            for link in android_page_links:
                link_text = link.get("text", "")
                link_href = link.get("href", "")
                for kw in publish_keywords:
                    if kw in link_text:
                        if link_href.startswith("http"):
                            bridge.navigate(link_href, wait_seconds=4.0)
                        else:
                            bridge.click(f'a:has-text("{link_text}")')
                        steps.append(f"✅ 通过链接进入发布页: 「{link_text}」")
                        clicked_publish = True
                        break
                if clicked_publish:
                    break
        
        if not clicked_publish:
            # 最后尝试直接 URL
            for fallback_path in [
                f"{admin_url}/admin/post.php?action=new",
                f"{admin_url}/admin/post.php?action=add",
                f"{admin_url}/admin/publish.php",
            ]:
                bridge.navigate(fallback_path, wait_seconds=4.0)
                fb_text = bridge.get_page_text(500)
                if "标题" in fb_text or "title" in fb_text.lower() or "发布" in fb_text:
                    steps.append(f"🔄 通过 URL 回退进入发布页: {fallback_path}")
                    clicked_publish = True
                    break
        
        if not clicked_publish:
            page_links_summary = "\n".join([
                f"  [{i}] {l.get('text','(空)')[:60]} → {l.get('href','')[:80]}"
                for i, l in enumerate(android_page_links[:30])
            ])
            steps.append(f"⚠️ 在安卓游戏页面未找到发布按钮，当前页面链接:\n{page_links_summary}")
            return "❌ 未找到发布入口。" + "\n".join(steps) + \
                   "\n\n💡 建议：先用 browse_page 查看安卓游戏页面内容，确认发布按钮的位置。"
        
        time.sleep(2)

        # ===== 步骤 6: 填写表单 =====
        _fill_form_via_bridge(bridge, title, intro, category, tags, download_url,
                              logo_path, screenshot_paths, resource_type)
        steps.append("📝 表单已填写")

        # ===== 步骤 7: 提交 =====
        time.sleep(1)
        submit_keywords = ["提交", "发布", "保存", "确认"]
        submitted = False
        for kw in submit_keywords:
            submit_selectors = [
                f'button[type="submit"]:has-text("{kw}")',
                f'button:has-text("{kw}")',
                f'input[type="submit"]:has-text("{kw}")',
                f'a:has-text("{kw}")',
                '.submit-btn', '#submit-btn',
            ]
            for sel in submit_selectors:
                result = bridge.click(sel)
                if "not_found" not in result and "超时" not in result:
                    steps.append(f"🚀 提交: {result}")
                    submitted = True
                    break
            if submitted:
                break
        
        if not submitted:
            # 万能回退：找 form 中任意 submit 按钮
            for sel in ['button[type="submit"]', 'input[type="submit"]', 'form button:last-child']:
                result = bridge.click(sel)
                if "not_found" not in result:
                    steps.append(f"🚀 回退提交: {result}")
                    submitted = True
                    break

        time.sleep(3)

        # ===== 步骤 8: 验证结果 =====
        current_title = bridge.get_page_title()
        page_text = bridge.get_page_text(500)
        if any(w in page_text for w in ["成功", "发布成功", "操作成功", "success"]):
            steps.append("✅ 发布成功!")
            return "✅ 发布成功!\n  标题: " + title + "\n\n" + "\n".join(steps)
        else:
            steps.append("⚠️ 发布已提交，请手动验证")
            return "⚠️ 发布已提交，请手动验证。" + "\n\n" + "\n".join(steps)

    except Exception as e:
        logger.error(f"❌ 发布失败: {e}")
        import traceback
        return f"❌ 发布失败: {e}\n{traceback.format_exc()}"


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
        escaped_category = json.dumps(category)
        for sel in ['select[name="category"]', '#category', 'select[name="type"]']:
            bridge.execute_js(f"""
                (function() {{
                    var el = document.querySelector('{sel}');
                    if (el) {{ el.value = {escaped_category}; el.dispatchEvent(new Event('change')); return 'ok'; }}
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
        escaped_tags = json.dumps(tags)
        for sel in ['input[name="tags"]', '#tags', 'input[placeholder*="标签"]']:
            bridge.execute_js(f"""
                (function() {{
                    var el = document.querySelector('{sel}');
                    if (el) {{ el.value = {escaped_tags}; el.dispatchEvent(new Event('input')); return 'ok'; }}
                    return 'not found';
                }})()
            """, timeout=2.0)
