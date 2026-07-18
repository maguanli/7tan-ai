"""
代码查看器 — 嵌入浏览器与控制台之间，支持语法高亮
"""
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QFileDialog, QTreeWidget, QTreeWidgetItem, QSplitter,
    QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class PythonHighlighter(QSyntaxHighlighter):
    """Python 语法高亮器 - Dracula 配色"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 预编译所有规则
        self._rules = []

        # 关键字 (粉红)
        kw = QTextCharFormat(); kw.setForeground(QColor("#ff79c6")); kw.setFontWeight(700)
        for w in ["and","as","assert","async","await","break","class","continue","def",
                  "del","elif","else","except","finally","for","from","global","if",
                  "import","in","is","lambda","nonlocal","not","or","pass","raise",
                  "return","try","while","with","yield","True","False","None","self","super"]:
            self._rules.append((rf'\b{w}\b', kw))

        # 字符串 (黄)
        s = QTextCharFormat(); s.setForeground(QColor("#f1fa8c"))
        for p in [r'"[^"\\]*(\\.[^"\\]*)*"', r"'[^'\\]*(\\.[^'\\]*)*'",
                  r'"""[^"]*"""', r"'''[^']*'''", r'f".*?"', r"f'.*?'"]:
            self._rules.append((p, s))

        # 注释 (灰)
        c = QTextCharFormat(); c.setForeground(QColor("#6272a4")); c.setFontItalic(True)
        self._rules.append((r'#.*$', c))

        # 装饰器 (绿)
        d = QTextCharFormat(); d.setForeground(QColor("#50fa7b")); d.setFontWeight(700)
        self._rules.append((r'@\w+', d))

        # 数字 (紫)
        n = QTextCharFormat(); n.setForeground(QColor("#bd93f9"))
        self._rules.append((r'\b\d+\.?\d*\b', n))

        # 函数调用 (绿)
        f = QTextCharFormat(); f.setForeground(QColor("#50fa7b"))
        self._rules.append((r'\b([a-zA-Z_]\w*)\s*\(', f))

        # 类名 (青)
        cl = QTextCharFormat(); cl.setForeground(QColor("#8be9fd")); cl.setFontWeight(700)
        self._rules.append((r'\b([A-Z][a-zA-Z0-9_]*)\b', cl))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for m in re.finditer(pattern, text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class CodeViewer(QWidget):
    """代码查看器：文件树 + 语法高亮编辑器"""

    file_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._current_file = None
        self._highlighter = None
        self._search_results = []  # [(file_path, line_no, line_text), ...]
        self._search_idx = -1
        self._file_cache = {}  # path -> content, for fast search

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- 工具栏 ----
        tb = QHBoxLayout(); tb.setContentsMargins(8, 6, 8, 4); tb.setSpacing(6)
        tb.addWidget(self._lbl("📝 代码", "#e2e8f0", 13, True))
        self._file_label = self._lbl("未打开文件", "#64748b", 11)
        tb.addWidget(self._file_label, 1)
        # 搜索框
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 搜索文件名或代码...")
        self._search_input.setFixedHeight(26)
        self._search_input.setFixedWidth(220)
        self._search_input.setStyleSheet(
            "QLineEdit{background:#0f0f23;color:#e2e8f0;border:1px solid #334155;"
            "border-radius:4px;font-size:12px;padding:2px 8px;}"
            "QLineEdit:focus{border-color:#00d4ff;}")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.returnPressed.connect(self._on_search)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        tb.addWidget(self._search_input)
        # 搜索结果计数
        self._search_count_label = self._lbl("", "#64748b", 10)
        self._search_count_label.setFixedWidth(50)
        tb.addWidget(self._search_count_label)
        # 上下导航
        for text, slot in [("▲", self._prev_match), ("▼", self._next_match)]:
            btn_nav = QPushButton(text)
            btn_nav.setFixedSize(24, 24)
            btn_nav.clicked.connect(slot)
            btn_nav.setStyleSheet("background:#334155;color:#e2e8f0;border:none;border-radius:3px;font-size:11px;")
            btn_nav.setCursor(Qt.CursorShape.PointingHandCursor)
            tb.addWidget(btn_nav)
        for text, color, slot in [("📂 打开", "#10b981", self._open_dialog),
                                   ("🔄 刷新", "#7c3aed", self._refresh_tree)]:
            btn = QPushButton(text); btn.setFixedHeight(26)
            btn.setFixedWidth(80 if len(text) > 2 else 36)
            btn.clicked.connect(slot)
            btn.setStyleSheet(f"background:{color};color:#fff;border:none;border-radius:4px;font-size:12px;font-weight:bold;")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            tb.addWidget(btn)
        layout.addLayout(tb)

        # ---- 分屏 ----
        vs = QSplitter(Qt.Orientation.Vertical); vs.setHandleWidth(3)
        vs.setStyleSheet("QSplitter::handle{background:#00d4ff44;margin:2px 0;border-radius:1px}"
                         "QSplitter::handle:hover{background:#00d4ff88}")

        # 文件树
        self._tree = QTreeWidget(); self._tree.setHeaderHidden(True); self._tree.setIndentation(16)
        self._tree.setMinimumHeight(80)
        self._tree.setStyleSheet("QTreeWidget{background:#0f0f23;color:#e2e8f0;border:1px solid #1e293b;font-size:12px}"
                                  "QTreeWidget::item:hover{background:#1e3a5f}"
                                  "QTreeWidget::item:selected{background:#00d4ff33}")
        self._tree.itemClicked.connect(self._on_click)
        vs.addWidget(self._tree)

        # 编辑器
        self._editor = QPlainTextEdit(); self._editor.setReadOnly(True)
        self._editor.setFont(QFont("Consolas", 11))
        self._editor.setStyleSheet("QPlainTextEdit{background:#1a1a2e;color:#e2e8f0;border:1px solid #1e293b;selection-background-color:#00d4ff44}")
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        vs.addWidget(self._editor)
        vs.setSizes([150, 350])
        layout.addWidget(vs, 1)

        # 状态栏
        self._status = self._lbl("就绪", "#64748b", 11)
        self._status.setStyleSheet("padding:2px 8px;")
        layout.addWidget(self._status)

        QTimer.singleShot(300, self._refresh_tree)
        QShortcut(QKeySequence("Ctrl+F"), self, self._focus_search)
        QShortcut(QKeySequence("Escape"), self, self._clear_search)

    def _lbl(self, text, color, size, bold=False):
        w = "bold;" if bold else ""
        l = QLabel(text); l.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{w}")
        return l

    def _refresh_tree(self):
        self._tree.clear()
        self._add_dir(PROJECT_ROOT, self._tree.invisibleRootItem())
        self._tree.expandToDepth(1)

    def _add_dir(self, path, parent):
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            for i, e in enumerate(entries):
                if i >= 60 or e.name.startswith('.'):
                    continue
                if e.name in ('__pycache__','node_modules','.git','dist','build','.venv','venv','.idea','.vscode','egg-info'):
                    continue
                if e.is_dir():
                    node = QTreeWidgetItem(parent, [f"📁 {e.name}"])
                    node.setData(0, Qt.ItemDataRole.UserRole, str(e))
                    node.setData(0, Qt.ItemDataRole.UserRole + 1, True)
                    if parent is self._tree.invisibleRootItem():
                        self._add_dir(e, node)
                elif e.suffix in ('.py','.json','.yaml','.yml','.txt','.md','.html','.css',
                                   '.js','.ts','.toml','.cfg','.ini','.bat','.sh','.xml',
                                   '.kt','.java','.swift','.c','.cpp','.h','.rs','.go'):
                    ico = {'py':'🐍','json':'📋','yaml':'⚙️','yml':'⚙️','txt':'📄','md':'📝',
                           'html':'🌐','css':'🎨','js':'📜','ts':'📘','toml':'⚙️','cfg':'⚙️',
                           'ini':'⚙️','bat':'⚡','sh':'🐚','xml':'📋','kt':'🅱️','java':'☕',
                           'swift':'🦅','c':'⚙️','cpp':'⚙️','h':'⚙️','rs':'🦀','go':'🐹'}.get(e.suffix,'📄')
                    node = QTreeWidgetItem(parent, [f"{ico} {e.name}"])
                    node.setData(0, Qt.ItemDataRole.UserRole, str(e))
                    node.setData(0, Qt.ItemDataRole.UserRole + 1, False)
        except PermissionError:
            pass

    def _on_click(self, item, col):
        if item.data(0, Qt.ItemDataRole.UserRole + 1):
            return
        p = item.data(0, Qt.ItemDataRole.UserRole)
        if p:
            self.open_file(p)

    def _open_dialog(self):
        p, _ = QFileDialog.getOpenFileName(self, "打开文件", str(PROJECT_ROOT),
            "代码 (*.py *.json *.yaml *.yml *.txt *.md *.html *.css *.js *.ts *.toml *.cfg *.ini *.bat *.sh *.xml *.kt *.java *.swift);;全部 (*)")
        if p:
            self.open_file(p)

    def open_file(self, path):
        try:
            p = Path(path)
            if not p.exists():
                self._status.setText(f"❌ 文件不存在: {path}")
                return
            content = p.read_text(encoding='utf-8', errors='replace')
            self._editor.setPlainText(content)
            if self._highlighter:
                self._highlighter.deleteLater(); self._highlighter = None
            if p.suffix == '.py':
                self._highlighter = PythonHighlighter(self._editor.document())
            self._current_file = str(p); self._file_label.setText(p.name)
            rel = p.relative_to(PROJECT_ROOT) if str(p).startswith(str(PROJECT_ROOT)) else p
            self._status.setText(f"✅ {rel} — {len(content)} 字符, {content.count(chr(10))+1} 行")
            self.file_selected.emit(str(p))
            self._highlight_in_tree(str(p))
        except Exception as e:
            self._status.setText(f"❌ 打开失败: {e}")

    def _highlight_in_tree(self, path):
        def find(items, target):
            for i in range(items.count()):
                it = items.item(i)
                if it.data(0, Qt.ItemDataRole.UserRole) == target:
                    self._tree.setCurrentItem(it); return True
                if find(it, target): return True
            return False
        find(self._tree.invisibleRootItem(), path)

    # ========== 搜索功能 ==========
    def _focus_search(self):
        """Ctrl+F 聚焦搜索框并全选"""
        self._search_input.setFocus()
        self._search_input.selectAll()

    def _clear_search(self):
        """Esc 清空搜索"""
        self._search_input.clear()
        self._search_results.clear()
        self._search_idx = -1
        self._search_count_label.setText("")
        self._clear_search_highlight()

    def _on_search_text_changed(self, text):
        """搜索文本变化时实时搜索"""
        if len(text) >= 2:
            self._on_search()
        elif len(text) == 0:
            self._search_results.clear()
            self._search_idx = -1
            self._search_count_label.setText("")
            self._clear_search_highlight()

    def _on_search(self):
        """执行搜索：先搜文件名，再搜代码内容"""
        query = self._search_input.text().strip()
        if len(query) < 2:
            self._search_count_label.setText("≥2字")
            return
        self._search_results.clear()
        self._search_idx = -1
        qlower = query.lower()
        # 1) 搜索文件名
        file_matches = []
        code_matches = []
        self._collect_all_files(PROJECT_ROOT, qlower, file_matches, code_matches)
        # 文件名匹配放前面
        self._search_results = file_matches + code_matches
        count = len(self._search_results)
        self._search_count_label.setText(f"{count}个")
        if count > 0:
            self._search_idx = 0
            self._goto_result(0)
        else:
            self._search_count_label.setText("0个")

    def _collect_all_files(self, dir_path, qlower, file_matches, code_matches):
        """递归收集匹配文件"""
        try:
            for e in sorted(dir_path.iterdir(), key=lambda x: x.name.lower()):
                if e.name.startswith('.') or e.name in (
                    '__pycache__','node_modules','.git','dist','build',
                    '.venv','venv','.idea','.vscode','egg-info'):
                    continue
                if e.is_dir():
                    self._collect_all_files(e, qlower, file_matches, code_matches)
                elif e.suffix in (
                    '.py','.json','.yaml','.yml','.txt','.md','.html','.css',
                    '.js','.ts','.toml','.cfg','.ini','.bat','.sh','.xml',
                    '.kt','.java','.swift','.c','.cpp','.h','.rs','.go'):
                    # 文件名匹配
                    if qlower in e.name.lower():
                        file_matches.append((str(e), -1, f"📄 文件名匹配: {e.name}"))
                    # 代码内容匹配
                    try:
                        content = e.read_text(encoding='utf-8', errors='replace')
                        self._file_cache[str(e)] = content
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if qlower in line.lower():
                                code_matches.append((str(e), i + 1, line.strip()[:120]))
                                if len(code_matches) >= 200:
                                    return
                    except Exception:
                        pass
        except PermissionError:
            pass

    def _goto_result(self, idx):
        """跳转到第 idx 个搜索结果"""
        if not self._search_results:
            return
        self._search_idx = idx % len(self._search_results)
        file_path, line_no, line_text = self._search_results[self._search_idx]
        self._search_count_label.setText(f"{self._search_idx + 1}/{len(self._search_results)}")
        # 打开文件
        self.open_file(file_path)
        # 如果是代码行匹配，跳转到对应行并高亮
        if line_no > 0:
            self._highlight_line(line_no)

    def _next_match(self):
        if self._search_results:
            self._goto_result((self._search_idx + 1) % len(self._search_results))

    def _prev_match(self):
        if self._search_results:
            self._goto_result((self._search_idx - 1) % len(self._search_results))

    def _highlight_line(self, line_no):
        """高亮并滚动到指定行"""
        doc = self._editor.document()
        block = doc.findBlockByLineNumber(line_no - 1)
        if block.isValid():
            cursor = self._editor.textCursor()
            cursor.setPosition(block.position())
            cursor.movePosition(
                cursor.MoveOperation.NextCharacter,
                cursor.MoveMode.KeepAnchor,
                min(block.length() - 1, 200)
            )
            self._editor.setTextCursor(cursor)
            self._editor.centerCursor()
            # 临时高亮
            extra = self._editor.extraSelections()
            sel = type(extra[0])() if extra else type(self._editor)()
            fmt = sel.format if hasattr(sel, 'format') else None
            from PyQt6.QtWidgets import QTextEdit
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor("#fbbf2433"))
            sel.format.setUnderlineStyle(
                sel.format.UnderlineStyle.SingleUnderline
            )
            sel.format.setUnderlineColor(QColor("#fbbf24"))
            sel.cursor = cursor
            self._editor.setExtraSelections([sel])

    def _clear_search_highlight(self):
        """清除搜索高亮"""
        self._editor.setExtraSelections([])

    def show_file(self, path):
        self.open_file(path)
