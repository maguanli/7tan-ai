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

# 全局 WebEngine 视图引用（源网站 + 管理后台 双浏览器）
_web_view = None        # 源网站浏览器
_admin_web_view = None  # 管理后台浏览器
_active_context = "source"  # 当前活跃的浏览器上下文


def register_web_view(view, context: str = "source"):
    """BrowserPage 创建后注册 QWebEngineView 实例并初始化 Bridge"""
    global _web_view, _admin_web_view
    if context == "admin":
        _admin_web_view = view
    else:
        _web_view = view
    # 同时注册到 BrowserBridge
    from .browser_bridge import register_bridge, register_admin_bridge
    if context == "admin":
        register_admin_bridge(view)
    else:
        register_bridge(view)
    logger.info(f"✅ QWebEngineView 已注册 [{context}] -> browser_tools + BrowserBridge")


@register_tool(
    name="use_admin_browser",
    description="切换到管理后台浏览器窗口。之后所有浏览器操作（浏览/点击/填表）都将在管理后台页面执行。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="browser",
    requires_browser=True,
)
def use_admin_browser() -> str:
    """切换到管理后台浏览器"""
    global _active_context
    _active_context = "admin"
    return "✅ 已切换到管理后台浏览器窗口"


@register_tool(
    name="use_source_browser",
    description="切换到源网站浏览器窗口。之后所有浏览器操作（浏览/点击/下载）都将在源网站页面执行。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="browser",
    requires_browser=True,
)
def use_source_browser() -> str:
    """切换到源网站浏览器"""
    global _active_context
    _active_context = "source"
    return "✅ 已切换到源网站浏览器窗口"


def _get_active_view():
    """获取当前活跃的 WebEngineView"""
    global _web_view, _admin_web_view, _active_context
    if _active_context == "admin" and _admin_web_view is not None:
        return _admin_web_view
    return _web_view


def _get_bridge():
    """获取当前活跃浏览器的 Bridge 实例（线程安全）"""
    from .browser_bridge import get_bridge, get_admin_bridge
    global _active_context
    if _active_context == "admin":
        bridge = get_admin_bridge() or get_bridge()
    else:
        bridge = get_bridge()
    if bridge is None:
        raise RuntimeError("浏览器未启动（Bridge 未注册）")
    return bridge


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
    if _web_view is not None:
        bridge = _get_bridge()
        bridge.navigate(url, wait_seconds)
        title = bridge.get_page_title()
        text = bridge.get_page_text(10000)       # 读取更多文本 (之前 5000)
        link_list = bridge.get_page_links(200)    # 提取200个链接（含onclick/data-url）
        image_list = bridge.get_page_images(50)

        result = f"📄 页面标题: {title}\n\n📝 页面内容 (前10000字):\n{text[:10000]}\n"
        result += f"\n🔗 全部链接 ({len(link_list)}个):\n"
        for link in link_list[:80]:               # 显示前 80 个
            href = link.get('href', '')
            text = link.get('text', '') or '(无文字)'
            # 高亮下载链接
            is_dl = any(k in href.lower() for k in ['.apk', '.ipa', '.zip', '.rar', '.7z', '.exe',
                       'download', 'down', 'apk'])
            prefix = "📦 " if is_dl else "  - "
            result += f"{prefix}{text}: {href}\n"
        result += f"\n🖼️ 图片 ({len(image_list)}个, 显示前25):\n"
        for img in image_list[:25]:               # 显示前 25 个 (之前 20)
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
    if _web_view is None:
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
            result += f"\n📋 页面其他链接 ({len(other_links)}个, 显示前20):\n"
            for link in other_links[:20]:
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
    dangerous=True,
)
def click_element(selector: str, text: str = None) -> str:
    """点击页面元素（线程安全）"""
    if _web_view is None:
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
    """对当前页面截图（线程安全）"""
    if _web_view is None:
        return "⚠️ 浏览器未打开"
    path = Path("data/screenshots") / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    ok = _get_bridge().screenshot(str(path))
    return f"✅ 截图已保存: {path}" if ok else f"❌ 截图失败: {path}"


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
    if _web_view is None:
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
    dangerous=True,
)
def login_7tan(username: str, password: str) -> str:
    """自动登录 7坛 管理后台（线程安全）"""
    if _web_view is not None:
        bridge = _get_bridge()
        login_url = "https://img.7tan.cn/admin"

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
            resp = session.post("https://img.7tan.cn/login.php", data={
                "username": username, "password": password
            }, timeout=10)
            return "✅ 登录请求已发送" if resp.status_code == 200 else f"⚠️ 返回 {resp.status_code}"
        except Exception as e:
            return f"❌ 登录失败: {e}"


def close_browser():
    """释放浏览器引用和 Bridge"""
    global _web_view
    _web_view = None
    from .browser_bridge import unregister_bridge
    unregister_bridge()
    logger.info("🔌 浏览器引用已释放")
