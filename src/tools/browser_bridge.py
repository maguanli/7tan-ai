"""
浏览器桥接层 — 线程安全的 Qt WebEngine 操作代理
解决 AI Agent 工作线程直接操作 QWebEngineView 导致的 UI 冻结问题

工作原理：
  AI 工作线程 → invokeMethod (BlockingQueuedConnection) → 主线程执行 → 返回结果
"""
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSlot, QUrl, QTimer
from loguru import logger


class BrowserBridge(QObject):
    """
    线程安全的浏览器操作桥接器。

    所有方法都可以从任意线程调用，内部自动将操作调度到 Qt 主线程执行。
    使用 threading.Event 在工作线程异步等待 JS 回调。
    """

    # 信号：通知 UI 切换到分屏模式
    split_view_requested = None  # 由 MainWindow 连接，类型: pyqtSignal(bool)

    def __init__(self, web_view, parent=None):
        super().__init__(parent)
        self._web_view = web_view
        self._pending_js_result = None
        self._js_done = threading.Event()
        self._navigate_timeout = 30.0  # 导航超时（秒）
        self._operation_lock = threading.Lock()
        self._next_files = []  # 文件上传队列

    # ===== 导航 =====

    def navigate(self, url: str, wait_seconds: float = 3.0) -> str:
        """
        导航到 URL 并等待加载（线程安全）。

        Returns:
            str: 页面标题
        """
        # 在主线程执行导航
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self, "_navigate_impl",
            Qt.ConnectionType.BlockingQueuedConnection,
            Q_ARG(str, url)
        )

        # 等待页面加载
        time.sleep(wait_seconds)

        # 获取标题
        title = self.execute_js("document.title", timeout=3.0)
        return title or ""

    @pyqtSlot(str)
    def _navigate_impl(self, url: str):
        """在主线程执行导航"""
        self._web_view.load(QUrl(url))
        logger.debug(f"🌐 [Bridge] 导航到: {url}")

    # ===== JS 执行 =====

    def execute_js(self, js: str, timeout: float = 5.0) -> str:
        """
        在主线程执行 JavaScript 并同步等待结果（线程安全）。

        Args:
            js: JavaScript 代码
            timeout: 超时时间（秒）

        Returns:
            str: JS 执行结果
        """
        self._js_done.clear()
        self._pending_js_result = None

        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self, "_execute_js_impl",
            Qt.ConnectionType.BlockingQueuedConnection,
            Q_ARG(str, js)
        )

        # 等待主线程完成（runJavaScript 回调）
        if not self._js_done.wait(timeout):
            logger.warning(f"⏰ [Bridge] JS 执行超时 ({timeout}s): {js[:80]}")
            return ""
        return self._pending_js_result or ""

    @pyqtSlot(str)
    def _execute_js_impl(self, js: str):
        """在主线程执行 JS，通过回调通知工作线程（不阻塞主线程事件循环）"""
        def _on_js_done(val):
            self._pending_js_result = str(val) if val is not None else ""
            self._js_done.set()

        self._web_view.page().runJavaScript(js, _on_js_done)
        # 超时保护：30 秒后强制释放等待线程
        QTimer.singleShot(30000, lambda: self._js_done.is_set() or self._js_done.set())

    # ===== 截图 =====

    def screenshot(self, filepath: str) -> bool:
        """
        对当前页面截图（线程安全）。

        Returns:
            bool: 是否成功
        """
        self._js_done.clear()
        self._pending_js_result = None

        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self, "_screenshot_impl",
            Qt.ConnectionType.BlockingQueuedConnection,
            Q_ARG(str, filepath)
        )

        if not self._js_done.wait(10.0):
            logger.warning(f"⏰ [Bridge] 截图超时: {filepath}")
            return False
        return self._pending_js_result == "ok"

    @pyqtSlot(str)
    def _screenshot_impl(self, filepath: str):
        """在主线程执行截图"""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._web_view.grab().save(str(path))
            logger.debug(f"📸 [Bridge] 截图已保存: {filepath}")
            self._pending_js_result = "ok"
        except Exception as e:
            logger.error(f"📸 [Bridge] 截图失败: {e}")
            self._pending_js_result = "error"
        finally:
            self._js_done.set()

    # ===== 获取页面内容 =====

    def get_page_text(self, max_chars: int = 5000) -> str:
        """获取页面文本内容（线程安全）"""
        return self.execute_js(
            "document.body ? document.body.innerText : ''",
            timeout=3.0
        )[:max_chars]

    def get_page_links(self, max_links: int = 30) -> list:
        """获取页面链接列表 — 包含 onclick 提取的 URL（线程安全）"""
        import json
        js = f"""
        (function() {{
            var links = [];
            // 1. 标准 <a href> 链接
            Array.from(document.querySelectorAll('a[href]')).forEach(function(a) {{
                var href = a.href || '';
                var text = (a.innerText || '').trim().substring(0, 50);
                if (href && !href.startsWith('javascript:')) {{
                    links.push({{text: text, href: href}});
                }}
            }});
            // 2. 带 onclick 的元素 — 提取 URL
            Array.from(document.querySelectorAll('[onclick]')).forEach(function(el) {{
                var onclick = (el.getAttribute('onclick') || '').trim();
                var m = onclick.match(/(?:location\\.href|window\\.open|window\\.location|open)\\s*[=\\(]\\s*['"]([^'"]+)['"]/);
                if (!m) m = onclick.match(/(?:href|src)\\s*=\\s*['"]([^'"]+)['"]/);
                if (!m) m = onclick.match(/(https?:\\/\\/[^\\s'\"]+)/);
                if (m) {{
                    var text = (el.innerText || '').trim().substring(0, 50) || 'onclick';
                    links.push({{text: text, href: m[1]}});
                }}
            }});
            // 3. <button> 或 <div> 里的 data-url / data-href
            Array.from(document.querySelectorAll('[data-url],[data-href],[data-download]')).forEach(function(el) {{
                var url = el.getAttribute('data-url') || el.getAttribute('data-href') || el.getAttribute('data-download');
                if (url) {{
                    var text = (el.innerText || '').trim().substring(0, 50) || 'data-url';
                    links.push({{text: text, href: url}});
                }}
            }});
            return JSON.stringify(links.slice(0, {max_links}));
        }})()
        """
        result = self.execute_js(js, timeout=5.0)
        try:
            return json.loads(result)
        except Exception:
            return []

    def get_page_title(self) -> str:
        """获取页面标题（线程安全）"""
        return self.execute_js("document.title", timeout=2.0)

    def get_page_images(self, max_images: int = 50) -> list:
        """获取页面所有图片 URL 和描述（线程安全）"""
        import json
        js = f"""
        JSON.stringify(Array.from(document.querySelectorAll('img[src]'))
            .map(function(img) {{
                return {{
                    src: img.src,
                    alt: (img.alt || '').trim().substring(0, 100),
                    width: img.naturalWidth || img.width || 0,
                    height: img.naturalHeight || img.height || 0,
                    title: (img.title || '').trim().substring(0, 100),
                    className: (img.className || '').trim().substring(0, 100),
                }};
            }})
            .filter(function(img) {{
                // 过滤掉太小/太常见的图标
                var src = img.src.toLowerCase();
                var isDataUri = src.startsWith('data:');
                var isFavicon = src.includes('favicon') || src.includes('icon');
                var isTracking = src.includes('pixel') || src.includes('beacon') || src.includes('analytics');
                return !isDataUri && !isFavicon && !isTracking;
            }})
            .slice(0, {max_images}))
        """
        result = self.execute_js(js, timeout=5.0)
        try:
            return json.loads(result)
        except Exception:
            return []

    # ===== 点击操作 =====

    def click(self, selector: str, text: str = None) -> str:
        """
        点击页面元素（线程安全），支持 :has-text() 伪选择器和文本匹配。

        Args:
            selector: CSS 选择器，支持 :has-text("xxx") 扩展语法
            text: 按文本匹配（可选），会查找 innerText 包含该文本的元素

        Returns:
            str: 点击结果描述
        """
        self._js_done.clear()
        self._pending_js_result = None

        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self, "_click_impl",
            Qt.ConnectionType.BlockingQueuedConnection,
            Q_ARG(str, selector),
            Q_ARG(str, text or "")
        )

        # 等待 JS 回调返回结果
        if not self._js_done.wait(8.0):
            logger.warning(f"⏰ [Bridge] 点击超时: {selector}")
            return f"⏰ 点击超时: {selector}"
        return self._pending_js_result or f"已点击: {selector}"

    @pyqtSlot(str, str)
    def _click_impl(self, selector: str, text: str):
        """在主线程执行点击，支持按文本内容匹配"""
        js_escaped_selector = selector.replace("\\", "\\\\").replace("'", "\\'")
        text_escaped = text.replace("\\", "\\\\").replace("'", "\\'") if text else ""

        if text:
            # 按 selector + 包含的文本查找
            js = f"""
(function() {{
    var selector = '{js_escaped_selector}';
    var searchText = '{text_escaped}';
    var elements;

    // 处理 :has-text() 伪选择器（非标准 CSS，转为 JS 筛选）
    var hasTextMatch = selector.match(/^(.+?):has-text\\(["'](.+?)["']\\)$/);
    if (hasTextMatch) {{
        selector = hasTextMatch[1];
        searchText = hasTextMatch[2];
    }}

    try {{
        elements = document.querySelectorAll(selector);
    }} catch(e) {{
        return 'selector_error: ' + e.message;
    }}

    for (var i = 0; i < elements.length; i++) {{
        var el = elements[i];
        var elText = (el.innerText || el.textContent || el.value || '').trim();
        if (elText.indexOf(searchText) !== -1) {{
            el.scrollIntoView({{block: 'center', behavior: 'instant'}});
            el.click();
            return 'clicked: ' + el.tagName + ' text="' + elText.substring(0,50) + '"';
        }}
    }}

    // 回退：如果没找到文本匹配，尝试只按 selector 点击第一个
    if (elements.length > 0) {{
        elements[0].scrollIntoView({{block: 'center', behavior: 'instant'}});
        elements[0].click();
        return 'clicked_fallback: ' + elements[0].tagName + ' (no text match for "' + searchText + '")';
    }}

    return 'not_found: no element matches "' + selector + '"';
}})()
"""
        else:
            # 纯选择器匹配，但同样支持 :has-text()
            js = f"""
(function() {{
    var selector = '{js_escaped_selector}';

    var hasTextMatch = selector.match(/^(.+?):has-text\\(["'](.+?)["']\\)$/);
    if (hasTextMatch) {{
        selector = hasTextMatch[1];
        var searchText = hasTextMatch[2];
        try {{
            var elements = document.querySelectorAll(selector);
        }} catch(e) {{
            return 'selector_error: ' + e.message;
        }}
        for (var i = 0; i < elements.length; i++) {{
            var el = elements[i];
            var elText = (el.innerText || el.textContent || el.value || '').trim();
            if (elText.indexOf(searchText) !== -1) {{
                el.scrollIntoView({{block: 'center', behavior: 'instant'}});
                el.click();
                return 'clicked: ' + el.tagName + ' text="' + elText.substring(0,50) + '"';
            }}
        }}
        return 'not_found: no element with text "' + searchText + '" under "' + selector + '"';
    }}

    try {{
        var el = document.querySelector(selector);
    }} catch(e) {{
        return 'selector_error: ' + e.message;
    }}
    if (!el) return 'not_found: "' + selector + '"';
    el.scrollIntoView({{block: 'center', behavior: 'instant'}});
    el.click();
    return 'clicked: ' + el.tagName;
}})()
"""

        def _on_click_done(val):
            result = str(val) if val is not None else "clicked"
            logger.debug(f"🖱️ [Bridge] 点击结果: {result}")
            self._pending_js_result = result
            self._js_done.set()
        self._web_view.page().runJavaScript(js, _on_click_done)
        # 超时保护
        QTimer.singleShot(8000, lambda: self._js_done.is_set() or self._js_done.set())

    def upload_files(self, selector: str, file_paths: list) -> str:
        """
        上传文件到文件输入框 — 使用 base64 注入绕过文件对话框。
        JS 无法触发 file input 的 chooseFiles，所以直接用 JS File API 注入文件。

        Returns:
            str: "uploaded_N_files" 或错误信息
        """
        import os, base64
        valid = []
        for f in file_paths:
            f = str(f)
            if os.path.exists(f):
                valid.append(f)
        if not valid:
            return "no_valid_files"

        # 用 Python 读取文件并 base64 → JS 注入 FileList
        files_js = []
        for fp in valid:
            with open(fp, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode()
            fname = os.path.basename(fp)
            files_js.append(f'["{fname}","{b64}"]')
        files_json = "[" + ",".join(files_js) + "]"

        js = f"""
        (function() {{
            var files_data = {files_json};
            var el = document.querySelector('{selector}');
            if (!el || el.type !== 'file') return 'selector_not_found';

            var dt = new DataTransfer();
            files_data.forEach(function(fd) {{
                var name = fd[0];
                var b64 = fd[1];
                var binary = atob(b64);
                var bytes = new Uint8Array(binary.length);
                for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
                var mime = name.endsWith('.png') ? 'image/png' : 
                          name.endsWith('.jpg') || name.endsWith('.jpeg') ? 'image/jpeg' : 
                          'application/octet-stream';
                var file = new File([bytes], name, {{type: mime}});
                dt.items.add(file);
            }});
            el.files = dt.files;
            el.dispatchEvent(new Event('change', {{bubbles: true}}));
            el.dispatchEvent(new Event('input', {{bubbles: true}}));
            return 'uploaded_{len(valid)}';
        }})()
        """

        result = self.execute_js(js, timeout=10.0)
        return result if result else f"uploaded_{len(valid)}_files"

    def scroll_bottom(self):
        """滚动到页面底部（触发懒加载）"""
        self.execute_js("window.scrollTo(0, document.body.scrollHeight);", timeout=1.0)

    @property
    def is_available(self) -> bool:
        """浏览器是否可用"""
        return self._web_view is not None


# 全局桥接实例
_bridge: BrowserBridge | None = None
_admin_bridge: BrowserBridge | None = None


def register_bridge(web_view) -> BrowserBridge:
    """注册主窗口 QWebEngineView（主线程调用）"""
    global _bridge
    _bridge = BrowserBridge(web_view)
    logger.info("✅ BrowserBridge 已注册")
    return _bridge


def register_admin_bridge(web_view) -> BrowserBridge:
    """注册管理后台窗口 QWebEngineView（主线程调用）"""
    global _admin_bridge
    _admin_bridge = BrowserBridge(web_view)
    logger.info("✅ BrowserBridge [管理后台] 已注册")
    return _admin_bridge


def get_bridge() -> BrowserBridge | None:
    """获取主窗口桥接实例"""
    return _bridge


def get_admin_bridge() -> BrowserBridge | None:
    """获取管理后台桥接实例"""
    return _admin_bridge


def unregister_bridge():
    global _bridge, _admin_bridge
    _bridge = None
    _admin_bridge = None
    logger.info("🔌 BrowserBridge 已释放")
