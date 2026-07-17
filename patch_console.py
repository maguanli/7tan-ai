"""Patch app.py to add ConsoleViewer to ChatBrowserSplitPage"""
import re

APP_PATH = r'D:\7tan\7tanAI\src\ui\app.py'

with open(APP_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already patched
if 'ConsoleViewer' in content:
    print("Already patched, skipping.")
    exit(0)

# === Step 1: Add import ===
old = "# ===== AI 工作台（浏览器 + 对话 左右分屏） ====="
new = "from .console_panel import ConsoleViewer\n\n# ===== AI 工作台（浏览器 + 对话 左右分屏） ====="
content = content.replace(old, new, 1)

# === Step 2: Add console_viewer + panel bar in __init__ ===
old_browsers = (
    '        self._browser_stack.addWidget(self.source_browser)\n'
    '        self._browser_stack.addWidget(self.admin_browser)\n'
    '\n'
    '        self.chat = ChatPage()\n'
    '\n'
    '        splitter.addWidget(self._browser_stack)\n'
    '        splitter.addWidget(self.chat)'
)

new_browsers = (
    '        self._browser_stack.addWidget(self.source_browser)\n'
    '        self._browser_stack.addWidget(self.admin_browser)\n'
    '        self.console_viewer = ConsoleViewer()\n'
    '        self._browser_stack.addWidget(self.console_viewer)\n'
    '\n'
    '        self.chat = ChatPage()\n'
    '\n'
    '        # ===== 左侧顶部：面板切换按钮栏 =====\n'
    '        self._panel_bar = QHBoxLayout()\n'
    '        self._panel_bar.setContentsMargins(4, 4, 4, 2)\n'
    '        self._panel_bar.setSpacing(6)\n'
    '\n'
    '        panel_label = QLabel("📺")\n'
    '        panel_label.setStyleSheet("font-size: 14px;")\n'
    '        self._panel_bar.addWidget(panel_label)\n'
    '\n'
    '        self._btn_source = self._make_panel_btn("🌐 源网站", True)\n'
    '        self._btn_admin = self._make_panel_btn("🔧 管理后台", False)\n'
    '        self._btn_console = self._make_panel_btn("📟 控制台", False)\n'
    '\n'
    '        self._btn_source.clicked.connect(lambda: self._switch_panel(0, self._btn_source))\n'
    '        self._btn_admin.clicked.connect(lambda: self._switch_panel(1, self._btn_admin))\n'
    '        self._btn_console.clicked.connect(lambda: self._switch_panel(2, self._btn_console))\n'
    '\n'
    '        self._panel_btns = [self._btn_source, self._btn_admin, self._btn_console]\n'
    '        for b in self._panel_btns:\n'
    '            self._panel_bar.addWidget(b)\n'
    '        self._panel_bar.addStretch()\n'
    '\n'
    '        # 左侧面板容器\n'
    '        left_container = QWidget()\n'
    '        left_layout = QVBoxLayout(left_container)\n'
    '        left_layout.setContentsMargins(0, 0, 0, 0)\n'
    '        left_layout.setSpacing(0)\n'
    '        left_layout.addLayout(self._panel_bar)\n'
    '        left_layout.addWidget(self._browser_stack, 1)\n'
    '\n'
    '        splitter.addWidget(left_container)\n'
    '        splitter.addWidget(self.chat)'
)

if old_browsers in content:
    content = content.replace(old_browsers, new_browsers, 1)
    print("Step 2: Browser panel patched.")
else:
    print("WARNING: old_browsers not found!")
    # Try to find what's actually there
    idx = content.find('self._browser_stack.addWidget(self.admin_browser)')
    if idx > 0:
        print("Context around target:")
        print(repr(content[idx:idx+200]))

# === Step 3: Add _make_panel_btn and _switch_panel methods ===
old_switch = (
    '    def switch_browser(self, target: str):\n'
    '        """切换显示的浏览器（线程安全 — 通过信号）"""\n'
    '        self._switch_signal.emit(target)'
)

new_switch = (
    '    def _make_panel_btn(self, text: str, active: bool = False):\n'
    '        """创建面板切换按钮"""\n'
    '        color = THEME[\'accent\'] if active else THEME[\'text_secondary\']\n'
    '        bg = f"{THEME[\'accent\']}33" if active else "transparent"\n'
    '        btn = QPushButton(text)\n'
    '        btn.setCheckable(True)\n'
    '        btn.setChecked(active)\n'
    '        btn.setFixedHeight(28)\n'
    '        btn.setStyleSheet(f"""\n'
    '            QPushButton {{\n'
    '                background: {bg}; color: {color};\n'
    '                border: 1px solid {THEME[\'border\']}; border-radius: 4px;\n'
    '                padding: 2px 10px; font-size: 11px; font-weight: bold;\n'
    '            }}\n'
    '            QPushButton:checked {{ background: {THEME[\'accent\']}44; color: {THEME[\'accent\']}; }}\n'
    '            QPushButton:hover {{ border-color: {THEME[\'accent\']}88; }}\n'
    '        """)\n'
    '        return btn\n'
    '\n'
    '    def _switch_panel(self, index: int, btn: QPushButton):\n'
    '        """切换左侧面板"""\n'
    '        self._browser_stack.setCurrentIndex(index)\n'
    '        for b in self._panel_btns:\n'
    '            b.setChecked(b is btn)\n'
    '        # 延迟初始化 admin/console\n'
    '        if index == 1 and len(self.admin_browser._tabs) == 0:\n'
    '            self.admin_browser._add_tab(url="https://img.7tan.cn/", title="7tan管理后台")\n'
    '\n'
    '    def switch_browser(self, target: str):\n'
    '        """切换显示的浏览器（线程安全 — 通过信号）"""\n'
    '        self._switch_signal.emit(target)'
)

if old_switch in content:
    content = content.replace(old_switch, new_switch, 1)
    print("Step 3: Panel methods patched.")
else:
    print("WARNING: old_switch not found!")

# === Step 4: Modify _do_switch_browser ===
old_do = (
    '    def _do_switch_browser(self, target: str):\n'
    '        """实际执行浏览器切换（仅主线程通过信号触发）"""\n'
    '        if target == "admin":\n'
    '            self._browser_stack.setCurrentIndex(1)\n'
    '            if len(self.admin_browser._tabs) == 0:\n'
    '                self.admin_browser._add_tab(url="https://img.7tan.cn/", title="7tan管理后台")\n'
    '        else:\n'
    '            self._browser_stack.setCurrentIndex(0)'
)

new_do = (
    '    def _do_switch_browser(self, target: str):\n'
    '        """实际执行浏览器切换（仅主线程通过信号触发）"""\n'
    '        if target == "admin":\n'
    '            self._switch_panel(1, self._btn_admin)\n'
    '        elif target == "console":\n'
    '            self._switch_panel(2, self._btn_console)\n'
    '        else:\n'
    '            self._switch_panel(0, self._btn_source)'
)

if old_do in content:
    content = content.replace(old_do, new_do, 1)
    print("Step 4: _do_switch_browser patched.")
else:
    print("WARNING: old_do not found!")

# === Step 5: Fix _open_source duplicate code ===
old_open = (
    '    def _open_source(self):\n'
    '        """切换到源网站"""\n'
    '        self.switch_browser("source")\n'
    '\n'
    '        splitter.addWidget(self.browser)\n'
    '        splitter.addWidget(self.chat)\n'
    '        splitter.setSizes([700, 540])\n'
    '        splitter.setStretchFactor(0, 3)\n'
    '        splitter.setStretchFactor(1, 2)\n'
    '\n'
    '        layout.addWidget(splitter)'
)

new_open = (
    '    def _open_source(self):\n'
    '        """切换到源网站"""\n'
    '        self.switch_browser("source")'
)

if old_open in content:
    content = content.replace(old_open, new_open, 1)
    print("Step 5: Fixed _open_source duplicate code.")
else:
    print("Step 5: old_open not found (may already be clean).")

# Write back
with open(APP_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Done! File size: {len(content)} chars")
