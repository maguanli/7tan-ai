"""
浏览器操作工具 — 基于 PyQt6 QWebEngineView 原生内核
通过 BrowserBridge 实现线程安全的跨线程浏览器操作
AI Agent 工作线程 → Bridge (BlockingQueuedConnection) → Qt 主线程
"""
import time
import json
from pathlib import Path

import requests
from loguru import logger
from .registry import register_tool

# 全局 WebEngine 视图引用 — 支持源站 + 管理后台双窗口
_source_view = None   # 主窗口浏览器（源网站）
_admin_view = None    # 管理后台浏览器（独立窗口）
_active_ctx = "source"  # 当前操作目标
_switch_ui_callback = None  # UI 回调：ChatBrowserSplitPage.switch_browser


def set_active_context(ctx: str):
    """设置当前操作的浏览器上下文，触发 UI 切换"""
    global _active_ctx, _switch_ui_callback
    _active_ctx = ctx
    if _switch_ui_callback:
        _switch_ui_callback(ctx)


def register_web_view(view, role: str = "source"):
    """注册 QWebEngineView。role: 'source'（主窗口）或 'admin'（管理后台窗口）"""
    global _source_view, _admin_view
    if role == "admin":
        _admin_view = view
    else:
        _source_view = view
    from .browser_bridge import register_bridge, register_admin_bridge
    if role == "admin":
        register_admin_bridge(view)
    else:
        register_bridge(view)
    # 处理 JS window.open() 弹窗 → 在当前视图打开（自动化点击不再被静默丢弃）
    try:
        view.page().setNewWindowRequestedHandler(
            lambda req, v=view: _open_new_window_in_view(v, req)
        )
    except Exception:
        pass
    logger.info(f"✅ BrowserView 已注册 [{role}]")


def _open_new_window_in_view(view, request):
    """处理 JS window.open() 弹窗：在当前视图打开 URL，避免被静默丢弃。

    微信公众平台等后台点击草稿/文章会用 window.open 打开编辑页，
    若不处理，QWebEngineView 会直接丢弃新窗口请求，导致点击无反应。
    """
    try:
        url = request.requestedUrl()
        if url.isValid() and not url.isEmpty():
            view.setUrl(url)
    except Exception:
        pass


def _get_active_view():
    global _source_view, _admin_view, _active_ctx
    if _active_ctx == "admin" and _admin_view is not None:
        return _admin_view
    return _source_view


def _get_bridge():
    """获取当前活跃浏览器的 Bridge 实例（线程安全）"""
    from .browser_bridge import get_bridge, get_admin_bridge
    global _active_ctx
    if _active_ctx == "admin":
        bridge = get_admin_bridge()
        if bridge is None:
            bridge = get_bridge()  # fallback
    else:
        bridge = get_bridge()
    if bridge is None:
        raise RuntimeError("浏览器未启动（Bridge 未注册）")
    return bridge


@register_tool(
    name="use_source_browser",
    description="切换到源网站浏览器。之后 browse_page/click_element 等操作都在游戏源站执行。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="browser",
    requires_browser=True,
)
def use_source_browser() -> str:
    set_active_context("source")
    return "✅ 已切回源网站浏览器"


@register_tool(
    name="use_admin_browser",
    description="切换到管理后台浏览器。之后 browse_page/click_element 等操作都在管理后台执行。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="browser",
    requires_browser=True,
)
def use_admin_browser() -> str:
    set_active_context("admin")
    # 自动打开管理后台页面
    try:
        from ..config.loader import load_config
        config = load_config()
        admin_url = config.get("site_7tan", {}).get("base_url", "")
        bridge = _get_bridge()
        bridge.navigate(f"{admin_url}/", wait_seconds=5.0)
        return f"✅ 已切换到管理后台，当前页面: {admin_url}/"
    except Exception as e:
        return f"✅ 已切换到管理后台（导航失败: {e}）"
    return "✅ 已切换到管理后台浏览器"


@register_tool(
    name="scroll_down",
    description="滚动到页面底部。列表页用无限滚动/懒加载时，必须先用这个滚到底触发加载，再browse_page才能读到全部内容。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="browser",
    requires_browser=True,
)
def scroll_down() -> str:
    bridge = _get_bridge()
    bridge.scroll_bottom()
    return "✅ 已滚动到底部"


def _exec_js(js: str, timeout: float = 5.0) -> str:
    """通过 Bridge 线程安全地执行 JS 并同步等待结果"""
    return _get_bridge().execute_js(js, timeout)


def _navigate(url: str, wait_seconds: float = 3.0) -> str:
    """通过 Bridge 线程安全地导航到 URL"""
    return _get_bridge().navigate(url, wait_seconds)


# ---------------------------------------------------------------------------
# 已注册的 AI 工具
# ---------------------------------------------------------------------------

@register_tool(
    name="browse_page",
    description="打开网页并获取页面内容摘要（含文字、链接和图片URL）。AI 可以读取页面文本，提取所有图片地址用于下载游戏LOGO/截图。",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "要浏览的网页 URL"},
            "wait_seconds": {"type": "integer", "description": "等待页面加载的秒数", "default": 3},
        },
        "required": ["url"]
    },
    category="browser",
    requires_browser=True,
)
def browse_page(url: str, wait_seconds: int = 3) -> str:
    """浏览网页 — GUI 模式用 Bridge（线程安全），无 GUI 用 requests"""
    if _source_view is not None:
        bridge = _get_bridge()
        bridge.navigate(url, wait_seconds)
        title = bridge.get_page_title()
        text = bridge.get_page_text(50000)       # 列表页面需要大容量
        link_list = bridge.get_page_links(200)    # 提取200个链接（含onclick/data-url）
        image_list = bridge.get_page_images(50)

        result = f"📄 页面标题: {title}\n\n📝 页面内容:\n{text}\n"
        result += f"\n🔗 全部链接 ({len(link_list)}个):\n"
        for link in link_list:                     # 全部链接
            href = link.get('href', '')
            text = link.get('text', '') or '(无文字)'
            # 高亮下载链接
            is_dl = any(k in href.lower() for k in ['.apk', '.ipa', '.zip', '.rar', '.7z', '.exe',
                       'download', 'down', 'apk'])
            prefix = "📦 " if is_dl else "  - "
            result += f"{prefix}{text}: {href}\n"
        result += f"\n🖼️ 图片 ({len(image_list)}个):\n"
        for img in image_list:                     # 全部图片
            size_info = f" ({img.get('width','?')}x{img.get('height','?')})" if img.get('width') else ""
            alt = img.get('alt', '') or img.get('title', '') or '(无描述)'
            cls_hint = ""
            cls = img.get('className', '').lower()
            if 'logo' in cls: cls_hint = " [LOGO]"
            elif 'screenshot' in cls or 'screen' in cls: cls_hint = " [截图]"
            elif 'gallery' in cls or 'carousel' in cls or 'slide' in cls: cls_hint = " [图集]"
            result += f"  - {alt}{cls_hint}{size_info}\n    {img.get('src', '')}\n"
        return result
    else:
        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            # 尝试从 HTML 中提取图片 URL
            import re as _re
            img_urls = _re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', resp.text, _re.IGNORECASE)
            result = f"📄 URL: {url}\n📝 响应内容 (前5000字符):\n{resp.text[:5000]}"
            if img_urls:
                result += f"\n\n🖼️ 页面图片 ({len(img_urls)}个, 前20):\n"
                for iu in img_urls[:20]:
                    result += f"  - {iu}\n"
            return result
        except Exception as e:
            return f"❌ 无法访问 {url}: {e}"


@register_tool(
    name="find_download_links",
    description="在当前浏览的页面中查找下载链接。自动识别游戏包(APK/IPA/ZIP/RAR/EXE等)的下载地址。用于从游戏下载站定位真正的下载URL。",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    category="browser",
    requires_browser=True,
)
def find_download_links() -> str:
    """在当前页面中智能搜索下载链接"""
    if _source_view is None:
        return "❌ 浏览器未就绪"

    bridge = _get_bridge()
    # 获取所有链接
    link_list = bridge.get_page_links(200)

    # 下载文件扩展名
    download_exts = ['.apk', '.ipa', '.zip', '.rar', '.7z', '.exe', '.msi',
                     '.dmg', '.tar.gz', '.tar.xz', '.gz', '.bz2', '.xz']

    # 下载关键词
    download_keywords = ['download', '下载', '立即下载', '本地下载', '高速下载',
                         '安卓下载', '苹果下载', 'android', 'ios', 'apk',
                         'down', 'dl', 'getfile']

    # 第一轮：精确匹配文件扩展名
    exact_matches = []
    # 第二轮：链接文本或URL含下载关键词
    keyword_matches = []
    # 第三轮：其他链接
    other_links = []

    for link in link_list:
        href = link.get('href', '').lower()
        text = (link.get('text', '') or '').lower()
        full = href + ' ' + text

        is_exact = any(ext in href for ext in download_exts)
        is_keyword = any(kw in full for kw in download_keywords)

        if is_exact:
            exact_matches.append(link)
        elif is_keyword:
            keyword_matches.append(link)
        else:
            other_links.append(link)

    result = "🔍 页面下载链接分析:\n\n"

    if exact_matches:
        result += f"✅ 精确匹配 ({len(exact_matches)}个) — 最可能是下载链接:\n"
        for link in exact_matches:
            result += f"  📦 {link.get('text', '') or '(无文字)'}\n"
            result += f"     URL: {link.get('href', '')}\n"
        result += "\n"

    if keyword_matches:
        result += f"⚠️ 关键词匹配 ({len(keyword_matches)}个) — 可能是下载链接:\n"
        for link in keyword_matches:
            result += f"  🔗 {link.get('text', '') or '(无文字)'}\n"
            result += f"     URL: {link.get('href', '')}\n"
        result += "\n"

    if not exact_matches and not keyword_matches:
        result += "❌ 未找到明显的下载链接。\n"
        if other_links:
            result += f"\n📋 页面其他链接 ({len(other_links)}个):\n"
            for link in other_links:
                text = link.get('text', '') or '(无文字)'
                if len(text) > 40:
                    text = text[:40] + '...'
                result += f"  - {text}\n    {link.get('href', '')}\n"

    result += f"\n💡 提示: 如果下载地址仍未出现，可能需要先点击页面上的下载按钮来触发真实的下载链接。"
    return result


@register_tool(
    name="click_element",
    description="在浏览器中点击指定元素。用于导航、翻页、触发下载等。",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS 选择器"},
            "text": {"type": "string", "description": "按包含的文本点击（可选）"},
        },
        "required": ["selector"]
    },
    category="browser",
    requires_browser=True,
)
def click_element(selector: str, text: str = None) -> str:
    """点击页面元素（线程安全）"""
    if _source_view is None:
        return "⚠️ 浏览器未打开，请先切换到「浏览器」页面"
    return _get_bridge().click(selector, text)


@register_tool(
    name="screenshot",
    description="对当前页面截图，保存到本地",
    parameters={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "截图文件名（不含路径）"},
        },
        "required": ["filename"]
    },
    category="browser",
    requires_browser=True,
)
def screenshot(filename: str) -> str:
    """对当前页面截图（线程安全）。

    WebView 失效时自动回退系统屏幕截图（mss/pyautogui），
    保证截图功能永远可用，并明确告知截图方式。
    """
    path = Path("data/screenshots") / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    # 当前活跃视图是否有效
    view = _get_active_view()
    view_ok = False
    if view is not None:
        try:
            view_ok = view.page() is not None
        except RuntimeError:
            view_ok = False
        except Exception:
            view_ok = False

    if not view_ok:
        # WebView 已销毁 → 系统级截图兜底（不依赖 bridge）
        from .browser_bridge import _fallback_system_screenshot
        ok = _fallback_system_screenshot(str(path))
        if ok:
            logger.warning(f"🖥️ [screenshot] WebView 已销毁，已用系统截图兜底: {path}")
            return f"⚠️ 浏览器视图已失效，已用【系统屏幕截图】兜底保存: {path}"
        return f"❌ 截图失败: 浏览器视图已销毁且系统截图不可用 ({path})"

    bridge = _get_bridge()
    if bridge is None:
        return "⚠️ 浏览器桥接未初始化"
    result = bridge.screenshot(str(path))
    if result:
        return f"✅ 截图已保存: {path}"
    return f"❌ 截图失败: {path}"


@register_tool(
    name="get_page_images",
    description="获取当前浏览器页面中所有图片的URL和描述信息。用于提取游戏LOGO、截图等图片地址以便下载。",
    parameters={
        "type": "object",
        "properties": {
            "max_images": {"type": "integer", "description": "最多返回多少图片", "default": 50},
        },
        "required": []
    },
    category="browser",
    requires_browser=True,
)
def get_page_images(max_images: int = 50) -> str:
    """获取当前页面所有图片 URL"""
    if _source_view is None:
        return "⚠️ 浏览器未打开，请先浏览网页"
    image_list = _get_bridge().get_page_images(max_images)
    if not image_list:
        return "📸 当前页面无图片"
    result = f"🖼️ 页面图片 ({len(image_list)}个):\n"
    for img in image_list[:max_images]:
        size_info = f" ({img.get('width','?')}x{img.get('height','?')})" if img.get('width') else ""
        alt = img.get('alt', '') or img.get('title', '') or '(无描述)'
        cls_hint = ""
        cls = img.get('className', '').lower()
        if 'logo' in cls: cls_hint = " [LOGO]"
        elif 'screenshot' in cls or 'screen' in cls: cls_hint = " [截图]"
        elif 'gallery' in cls or 'carousel' in cls or 'slide' in cls: cls_hint = " [图集]"
        result += f"  - {alt}{cls_hint}{size_info}\n    地址: {img.get('src', '')}\n"
    return result


@register_tool(
    name="login_7tan",
    description="登录 7坛管理后台。自动填写用户名密码并提交登录。",
    parameters={
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "7坛后台用户名"},
            "password": {"type": "string", "description": "7坛后台密码"},
        },
        "required": ["username", "password"]
    },
    category="browser",
    requires_browser=True,
)
def login_7tan(username: str = "", password: str = "") -> str:
    """自动登录 7坛 管理后台（线程安全）。
    
    优先从加密数据库获取凭据，.env 明文密码作为回退。
    如果数据库有有效 Token，则跳过浏览器登录。
    """
    # 尝试从加密数据库获取凭据
    if not username or not password:
        try:
            from ..database.db import get_admin_username, get_admin_password, get_admin_token
            if not username:
                username = get_admin_username()
            if not password:
                # Token 有效则不需要密码
                token = get_admin_token()
                if token:
                    logger.info("🔑 使用 JWT Token 认证（跳过浏览器登录）")
                    return f"✅ Token 认证有效（用户: {username}），无需浏览器登录"
                password = get_admin_password()
        except Exception as e:
            logger.warning(f"获取加密凭据失败: {e}")
    
    if not password:
        return "⚠️ 未配置管理员密码。请在设置中配置密码或 API Token。"
    
    if _source_view is not None:
        bridge = _get_bridge()
        from ..config.loader import load_config as _load_cfg
        _cfg = _load_cfg()
        login_url = _cfg.get("site_7tan", {}).get("base_url", "") + "/"

        # 安全转义 JS 字符串
        _u = json.dumps(username)
        _p = json.dumps(password)

        # 步骤 1: 导航到登录页
        logger.info(f"🔐 导航到 7坛 管理后台: {login_url}")
        bridge.navigate(login_url, wait_seconds=5.0)

        # 步骤 2: 填写用户名
        u_result = _exec_js(f"""
(function() {{
    var fields = document.querySelectorAll('input');
    var u = document.querySelector('input[name="username"], input[name="user"], input[name="email"], input[type="text"], input[type="email"]');
    if (!u) {{
        for (var i=0; i<fields.length; i++) {{
            if (fields[i].type === 'text' || fields[i].type === 'email') {{
                u = fields[i]; break;
            }}
        }}
    }}
    if (u) {{ u.value = {_u}; u.dispatchEvent(new Event('input', {{bubbles:true}})); u.dispatchEvent(new Event('change', {{bubbles:true}})); return 'filled_u:'+u.name; }}
    return 'no_username_field';
}})()
""", timeout=5.0)
        logger.info(f"👤 填写用户名: {u_result}")

        # 步骤 3: 填写密码
        p_result = _exec_js(f"""
(function() {{
    var fields = document.querySelectorAll('input');
    var p = document.querySelector('input[name="password"], input[name="pass"], input[name="pwd"], input[type="password"]');
    if (!p) {{
        for (var i=0; i<fields.length; i++) {{
            if (fields[i].type === 'password') {{ p = fields[i]; break; }}
        }}
    }}
    if (p) {{ p.value = {_p}; p.dispatchEvent(new Event('input', {{bubbles:true}})); p.dispatchEvent(new Event('change', {{bubbles:true}})); return 'filled_p'; }}
    return 'no_password_field';
}})()
""", timeout=5.0)
        logger.info(f"🔑 填写密码: {p_result}")

        # 步骤 4: 点击登录按钮
        time.sleep(0.5)
        click_result = _exec_js("""
(function() {
    var selectors = ['button[type=submit]', 'input[type=submit]', '.btn-primary', '#login-btn', 'button', 'input[type=button]'];
    var keywords = ['登录', '登 录', 'Login', 'Sign in', 'submit', '提交'];
    for (var s=0; s<selectors.length; s++) {
        var els = document.querySelectorAll(selectors[s]);
        for (var i=0; i<els.length; i++) {
            var txt = (els[i].innerText || els[i].value || '').trim();
            for (var k=0; k<keywords.length; k++) {
                if (txt.indexOf(keywords[k]) !== -1) {
                    els[i].click();
                    return 'clicked:' + selectors[s] + ' text=' + txt;
                }
            }
        }
    }
    var sb = document.querySelector('[type=submit]');
    if (sb) { sb.click(); return 'clicked:fallback-submit'; }
    var btns = document.querySelectorAll('button');
    if (btns.length > 0) { btns[btns.length-1].click(); return 'clicked:fallback-last-button'; }
    var f = document.querySelector('form');
    if (f) { f.submit(); return 'submitted:form'; }
    return 'no_button_found';
})()
""", timeout=5.0)
        logger.info(f"🖱️ 点击登录按钮: {click_result}")

        # 步骤 5: 等待跳转并验证
        time.sleep(3.0)
        current_url = _exec_js("window.location.href", timeout=3.0)
        page_title = bridge.get_page_title()

        if "login" not in current_url.lower() and "admin" in current_url.lower():
            return f"✅ 已成功登录 7坛 管理后台！当前页面: {page_title} ({current_url})"
        elif "dashboard" in current_url.lower() or "index" in current_url.lower():
            return f"✅ 登录成功！当前页面: {page_title}"
        else:
            # 检查是否有错误提示
            error_text = _exec_js("""
(function() {
    var e = document.querySelector('.error, .alert-danger, .msg-error, [class*="error"]');
    return e ? e.innerText.trim().substring(0,200) : '';
})()
""", timeout=3.0)
            if error_text:
                return f"⚠️ 登录可能失败，页面显示: {error_text}。当前 URL: {current_url}"
            return f"⚠️ 登录状态不确定。当前页面: {page_title}，URL: {current_url}"
    else:
        try:
            session = requests.Session()
            from ..config.loader import load_config as _load_cfg
            _cfg = _load_cfg()
            _login_url = _cfg.get("site_7tan", {}).get("login_url", "") or (
                _cfg.get("site_7tan", {}).get("base_url", "") + "/login.php"
            )
            resp = session.post(_login_url, data={
                "username": username, "password": password
            }, timeout=10)
            return "✅ 登录请求已发送" if resp.status_code == 200 else f"⚠️ 返回 {resp.status_code}"
        except Exception as e:
            return f"❌ 登录失败: {e}"


def close_browser():
    """释放浏览器引用和 Bridge"""
    global _source_view, _admin_view
    _source_view = None
    _admin_view = None
    from .browser_bridge import unregister_bridge
    unregister_bridge()
    logger.info("🔌 浏览器引用已释放")


@register_tool(
    name="browser_exec_js",
    description="在当前浏览器页面执行任意 JavaScript 并返回结果。用于填表、读取DOM、触发事件等高级操作。",
    parameters={
        "type": "object",
        "properties": {
            "js": {"type": "string", "description": "要执行的 JavaScript 代码"},
        },
        "required": ["js"]
    },
    category="browser",
    requires_browser=True,
)
def browser_exec_js(js: str) -> str:
    """执行 JS（线程安全）"""
    if _source_view is None and _admin_view is None:
        return "⚠️ 浏览器未打开"
    bridge = _get_bridge()
    if bridge is None:
        return "⚠️ 浏览器桥接未初始化"
    result = bridge.execute_js(js, timeout=10.0)
    return result or "(空结果)"


@register_tool(
    name="browser_set_value",
    description="设置浏览器页面上输入框的值（自动触发 input/change 事件，兼容 React 表单）。用于填写表单。",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS 选择器"},
            "value": {"type": "string", "description": "要设置的值"},
        },
        "required": ["selector", "value"]
    },
    category="browser",
    requires_browser=True,
)
def browser_set_value(selector: str, value: str) -> str:
    """设置输入框值（React 兼容，使用原生 setter + 事件触发）"""
    if _source_view is None and _admin_view is None:
        return "⚠️ 浏览器未打开"
    bridge = _get_bridge()
    if bridge is None:
        return "⚠️ 浏览器桥接未初始化"
    js_selector = selector.replace("\\", "\\\\").replace("'", "\\'")
    js_value = value.replace("\\", "\\\\").replace("'", "\\'")
    js = f"""
(function() {{
    var el = document.querySelector('{js_selector}');
    if (!el) return 'not_found: ' + '{js_selector}';
    var proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(el, '{js_value}');
    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    return 'set_ok: ' + el.value;
}})()
"""
    result = bridge.execute_js(js, timeout=10.0)
    return result or "(空结果)"
