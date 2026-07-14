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
        """获取页面链接列表（线程安全）"""
        import json
        js = """
        JSON.stringify(Array.from(document.querySelectorAll('a[href]'))
            .map(a => ({text: a.innerText.trim().substring(0,50), href: a.href}))
            .filter(l => l.href && !l.href.startsWith('javascript'))
            .slice(0, """ + str(max_links) + """))
        """
        result = self.execute_js(js, timeout=3.0)
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
        点击页面元素（线程安全）。

        Args:
            selector: CSS 选择器
            text: 按文本匹配（可选）
        """
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self, "_click_impl",
            Qt.ConnectionType.BlockingQueuedConnection,
            Q_ARG(str, selector),
            Q_ARG(str, text or "")
        )
        return f"✅ 已点击: {selector}"

    @pyqtSlot(str, str)
    def _click_impl(self, selector: str, text: str):
        """在主线程执行点击"""
        js = f"document.querySelector('{selector}').click()"
        self._web_view.page().runJavaScript(js)
        logger.debug(f"🖱️ [Bridge] 点击: {selector}")

    @property
    def is_available(self) -> bool:
        """浏览器是否可用"""
        return self._web_view is not None


# 全局桥接实例
_bridge: BrowserBridge | None = None


def register_bridge(web_view) -> BrowserBridge:
    """注册 QWebEngineView 并创建桥接实例（主线程调用）"""
    global _bridge
    _bridge = BrowserBridge(web_view)
    logger.info("✅ BrowserBridge 已注册")
    return _bridge


def get_bridge() -> BrowserBridge | None:
    """获取全局桥接实例（任意线程调用）"""
    return _bridge


def unregister_bridge():
    """释放桥接实例"""
    global _bridge
    _bridge = None
    logger.info("🔌 BrowserBridge 已释放")
