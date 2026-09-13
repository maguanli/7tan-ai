"""
发布工具 — 7坛管理后台自动发布
"""
import time
import json
import random

from loguru import logger
from .registry import register_tool


@register_tool(
    name="api_publish_to_7tan",
    description="通过API发布资源到7坛（替代浏览器自动化）。需要先配置管理员Token。如API不可用则自动回退到浏览器发布。",
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
            "developer": {"type": "string", "description": "开发商名称（如 西安西品网络科技有限公司）"},
            "beian": {"type": "string", "description": "备案号（如 陕ICP备16005864号-28A）"},
            "version": {"type": "string", "description": "版本号（如 v1.0.3）"},
            "system_require": {"type": "string", "description": "系统要求（如 Android 5.0+）", "default": "5.0"},
            "resource_type": {"type": "string", "description": "'game' 或 'software'", "default": "game"},
        },
        "required": ["title", "intro", "download_url"]
    },
    category="publish",
    requires_browser=False,
)
def api_publish_to_7tan(title: str, intro: str, download_url: str, category: str = "",
                        tags: str = "", logo_path: str = "", screenshot_paths: str = "",
                        developer: str = "", beian: str = "", version: str = "",
                        system_require: str = "5.0", resource_type: str = "game") -> str:
    """
    优先通过 API 发布，失败则回退到浏览器发布。
    """
    from ..security.auth_client import api_publish_resource
    from ..database.db import get_admin_token, get_admin_password, get_admin_username
    import json as _json

    steps = []

    # 步骤 1: 获取 Token
    token = get_admin_token()
    if not token:
        steps.append("WARN: No valid API Token, falling back to browser publish...")
        return publish_to_7tan(title, intro, download_url, category, tags,
                               logo_path, screenshot_paths, resource_type,
                               developer, beian, version, system_require)

    steps.append("KEY: Token valid, using API publish")

    # 步骤 2: Parse screenshot paths
    shot_list = []
    if screenshot_paths and screenshot_paths not in ("[]", '[""]'):
        try:
            shot_list = _json.loads(screenshot_paths) if isinstance(screenshot_paths, str) else screenshot_paths
        except Exception:
            pass

    # 步骤 3: API publish
    result = api_publish_resource(
        token=token,
        title=title,
        intro=intro,
        download_url=download_url,
        category=category,
        tags=tags,
        resource_type=resource_type,
        logo_path=logo_path,
        screenshot_paths=shot_list,
    )

    if result.get("success"):
        publish_id = result.get("publish_id", "?")
        publish_url = result.get("publish_url", "")
        msg = f"API publish success! ID: {publish_id} URL: {publish_url}"
        return msg

    # API failed, fallback to browser
    error_msg = result.get("message", "Unknown error")
    steps.append(f"WARN: API publish failed: {error_msg}")
    steps.append("FALLBACK: Using browser automation...")

    try:
        browser_result = publish_to_7tan(title, intro, download_url, category, tags,
                                         logo_path, screenshot_paths, resource_type,
                                         developer, beian, version, system_require)
        return "\n".join(steps) + "\n\n" + browser_result
    except Exception as e:
        return "\n".join(steps) + f"\n\nFAIL: Browser fallback also failed: {e}"


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
            "developer": {"type": "string", "description": "开发商名称（如 西安西品网络科技有限公司）"},
            "beian": {"type": "string", "description": "备案号（如 陕ICP备16005864号-28A）"},
            "version": {"type": "string", "description": "版本号（如 v1.0.3）"},
            "system_require": {"type": "string", "description": "系统要求（如 Android 5.0+）", "default": "5.0"},
            "resource_type": {"type": "string", "description": "'game' 或 'software'", "default": "game"},
        },
        "required": ["title", "intro", "download_url"]
    },
    category="publish",
    requires_browser=True,
)
def publish_to_7tan(title: str, intro: str, download_url: str, category: str = "",
                    tags: str = "", logo_path: str = "", screenshot_paths: str = "",
                    developer: str = "", beian: str = "", version: str = "",
                    system_require: str = "5.0", resource_type: str = "game") -> str:
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
        admin_url = config.get("site_7tan", {}).get("base_url", "")
        steps = []

        # ===== 编辑模式：URL 为 content_edit.php?id=xxx 时直接修改已有记录 =====
        import re as _re
        edit_id = None
        try:
            _u = bridge.execute_js('(function(){ return location.href; })()', timeout=3.0) or ""
            _m = _re.search(r'content_edit\.php\?id=(\d+)', _u)
            if _m and int(_m.group(1)) > 0:
                edit_id = int(_m.group(1))
        except Exception:
            pass

        if edit_id:
            steps.append(f"✏️ 编辑模式: content_edit.php?id={edit_id}，直接在当前页填写并保存")
            fill_report, all_filled = _fill_form_via_bridge(
                bridge, title, intro, category, tags, download_url,
                logo_path, screenshot_paths, resource_type,
                developer, beian, version, system_require)
            steps.append(fill_report)
            time.sleep(1)
            for sel in ['button[type="submit"]:has-text("保存")',
                        'button:has-text("保存")',
                        'input[type="submit"]:has-text("保存")',
                        'button[type="submit"]', 'input[type="submit"]']:
                result = bridge.click(sel)
                if "not_found" not in result and "超时" not in result:
                    steps.append(f"💾 保存: {result}")
                    break
            time.sleep(3)
            txt = bridge.get_page_text(500)
            if any(w in txt for w in ["成功", "操作成功", "success"]):
                steps.append("✅ 保存成功!")
                return "✅ 保存成功!\n  ID: " + str(edit_id) + "\n\n" + "\n".join(steps)
            return "⚠️ 保存已提交，请手动验证。\n\n" + "\n".join(steps)

        # ⚠️ 硬性检查：LOGO和截图必须存在本地才能发布
        import os as _os
        missing = []
        if not logo_path:
            missing.append("LOGO (logo_path 参数为空)")
        elif not _os.path.exists(str(logo_path)):
            missing.append(f"LOGO (文件不存在: {logo_path})")
        if not screenshot_paths or screenshot_paths in ("[]", '[""]'):
            missing.append("截图 (screenshot_paths 参数为空)")
        else:
            try:
                shots_list = json.loads(screenshot_paths) if isinstance(screenshot_paths, str) else screenshot_paths
                if not isinstance(shots_list, list) or len(shots_list) == 0:
                    missing.append("截图 (列表为空)")
                else:
                    for sp in shots_list:
                        if not _os.path.exists(str(sp)):
                            missing.append(f"截图 (文件不存在: {sp})")
            except (json.JSONDecodeError, Exception):
                missing.append("截图 (格式解析失败)")
        if not intro or len(intro) < 20:
            missing.append("简介 (太短，需要≥100字)")
        if not download_url:
            missing.append("下载链接")

        if missing:
            return "❌ 发布被拒绝，以下必填项缺失:\n  - " + "\n  - ".join(missing) + \
                   "\n\n💡 请先下载 LOGO 和截图（get_page_images → download_file），再调用 publish_to_7tan。"

        # 切换到管理后台上下文
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
        bridge.navigate(f"{admin_url}/", wait_seconds=5.0)
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
                bridge.navigate(f"{admin_url}/{href}", wait_seconds=4.0)
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
                f"{admin_url}/post.php?action=new",
                f"{admin_url}/post.php?action=add",
                f"{admin_url}/publish.php",
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
        fill_report, all_filled = _fill_form_via_bridge(
            bridge, title, intro, category, tags, download_url,
            logo_path, screenshot_paths, resource_type,
            developer, beian, version, system_require)
        steps.append(fill_report)

        if not all_filled:
            steps.append("⚠️ 部分必填字段未成功填写，请在提交前手动检查")
            return "⚠️ 表单填写不完整。\n" + fill_report + \
                   "\n\n💡 建议：使用 browse_page 查看发布页面的 HTML 结构，找到正确的输入框选择器后重新发布。"

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
                          logo_path, screenshot_paths, resource_type,
                          developer="", beian="", version="", system_require="5.0"):
    """通过 Bridge 执行 JS 填写发布表单，返回填写报告"""
    filled = {}
    not_found = {}

    # === 第1步: 填写标题 → name="ll_biaoti" ===
    r = bridge.execute_js(f"""
        (function() {{
            var el = document.querySelector('input[name="ll_biaoti"]');
            if (el) {{ el.value = {json.dumps(title)}; el.dispatchEvent(new Event('input',{{bubbles:true}})); el.dispatchEvent(new Event('change',{{bubbles:true}})); return 'ok'; }}
            return 'not found';
        }})()
    """, timeout=2.0)
    if "ok" in r:
        filled["1.标题"] = title[:30]
    else:
        not_found["1.标题"] = "未找到 ll_biaoti"
        return _make_report(filled, not_found)

    # === 第2步: 选择分类 → name="ll_idd" ===
    if category:
        r = bridge.execute_js(f"""
            (function() {{
                var cat = {json.dumps(category)};
                var el = document.querySelector('select[name="ll_idd"]');
                if (!el) return 'not found';
                for (var i = 0; i < el.options.length; i++) {{
                    var opt = el.options[i].text;
                    if (opt === cat || opt.indexOf(cat) >= 0 || cat.indexOf(opt) >= 0) {{
                        el.selectedIndex = i;
                        el.dispatchEvent(new Event('change',{{bubbles:true}}));
                        return 'ok:' + opt;
                    }}
                }}
                return 'no match';
            }})()
        """, timeout=2.0)
        if "ok:" in r:
            filled["2.分类"] = r.split(":",1)[1]
        else:
            not_found["2.分类"] = f"分类'{category}'未匹配 ll_idd 选项"

    # === 第3步: 填写简介 → name="ll_jie"（不要填 ll_gxts 那是更新说明） ===
    if intro and len(intro) > 10:
        r = bridge.execute_js(f"""
            (function() {{
                var el = document.querySelector('textarea[name="ll_jie"]');
                if (el) {{
                    el.value = {json.dumps(intro)};
                    el.dispatchEvent(new Event('input',{{bubbles:true}}));
                    el.dispatchEvent(new Event('change',{{bubbles:true}}));
                    return 'ok';
                }}
                return 'not found';
            }})()
        """, timeout=2.0)
        filled["3.简介"] = f"{'✓' if 'ok' in r else '✗'} ll_jie"
    else:
        filled["3.简介"] = f"⚠️ 内容太短({len(intro)}字)"

    # === 第4步: 上传LOGO ===

    # === 第4步: 上传LOGO → id="logoFile" ===
    if logo_path:
        try:
            result = bridge.upload_files('#logoFile', [logo_path])
            filled["4.LOGO"] = f"✅ {result}"
        except Exception as e:
            filled["4.LOGO"] = f"⚠️ {e}"

    # === 第5步: 上传截图 → id="screenshotFile" ===
    if screenshot_paths:
        try:
            shots = json.loads(screenshot_paths) if isinstance(screenshot_paths, str) else screenshot_paths
            if isinstance(shots, list) and shots:
                result = bridge.upload_files('#screenshotFile', shots)
                filled["5.截图"] = f"✅ {len(shots)}张 ({result})"
            else:
                filled["5.截图"] = "无"
        except Exception as e:
            filled["5.截图"] = f"⚠️ {e}"

    # === 下载链接 → name="ll_text"(安卓), 不要填 ll_url(那是iOS) ===
    if download_url:
        r = bridge.execute_js(f"""
            (function() {{
                var el = document.querySelector('textarea[name="ll_text"]');
                if (el) {{ el.value = '{download_url}'; el.dispatchEvent(new Event('input')); return 'ok'; }}
                return 'not found';
            }})()
        """, timeout=2.0)
        if "ok" in r:
            filled["下载链接"] = download_url[:50]
        else:
            not_found["下载链接"] = "未找到 ll_text"

    # === 系统要求 → name="ll_xitong" ===
    _xitong = system_require or '5.0'
    r = bridge.execute_js(f"""
        (function() {{
            var el = document.querySelector('input[name="ll_xitong"]');
            if (el) {{ el.value = {json.dumps(_xitong)}; el.dispatchEvent(new Event('input')); return 'ok'; }}
            return 'not found';
        }})()
    """, timeout=2.0)
    filled["系统要求"] = _xitong if "ok" in r else "未找到 ll_xitong"

    # === 开发商 → name="ll_kaifa" ===
    if developer:
        r = bridge.execute_js(f"""
            (function() {{
                var el = document.querySelector('input[name="ll_kaifa"]');
                if (el) {{ el.value = {json.dumps(developer)}; el.dispatchEvent(new Event('input')); return 'ok'; }}
                return 'not found';
            }})()
        """, timeout=2.0)
        filled["开发商"] = developer if "ok" in r else "未找到 ll_kaifa"
    else:
        filled["开发商"] = "（未提供，跳过）"

    # === 备案号 → name="ll_beian" ===
    if beian:
        r = bridge.execute_js(f"""
            (function() {{
                var el = document.querySelector('input[name="ll_beian"]');
                if (el) {{ el.value = {json.dumps(beian)}; el.dispatchEvent(new Event('input')); return 'ok'; }}
                return 'not found';
            }})()
        """, timeout=2.0)
        filled["备案号"] = beian if "ok" in r else "未找到 ll_beian"

    # === 版本号 → name="ll_banben" ===
    if version:
        r = bridge.execute_js(f"""
            (function() {{
                var el = document.querySelector('input[name="ll_banben"]');
                if (el) {{ el.value = {json.dumps(version)}; el.dispatchEvent(new Event('input')); return 'ok'; }}
                return 'not found';
            }})()
        """, timeout=2.0)
        filled["版本号"] = version if "ok" in r else "未找到 ll_banben"

    # === 标签 ===
    if tags:
        for sel in ['input[name="ll_tags"]', 'input[name="tags"]', '#tags']:
            r = bridge.execute_js(f"""
                (function() {{
                    var el = document.querySelector('{sel}');
                    if (el) {{ el.value = {json.dumps(tags)}; el.dispatchEvent(new Event('input')); return 'ok'; }}
                    return 'not found';
                }})()
            """, timeout=2.0)
            if "ok" in r:
                filled["标签"] = tags
                break
        else:
            filled["标签"] = "⚠️ 站点无标签字段，已忽略（不阻塞发布）"

    # === 生成报告 ===

    # === 生成报告 ===
    report_parts = []
    for k in sorted(filled.keys()):
        report_parts.append(f"  ✅ {k}: {filled[k]}")
    for k in not_found:
        report_parts.append(f"  ❌ {k}: {not_found[k]}")

    report = "📝 填写报告（按用户要求的5步顺序）:\n" + "\n".join(report_parts)
    logger.info(report)
    return report, len(not_found) == 0


def _make_report(filled, not_found):
    parts = [f"  ✅ {k}: {v}" for k, v in filled.items()]
    parts += [f"  ❌ {k}: {v}" for k, v in not_found.items()]
    return "📝 " + "\n".join(parts)
