"""
代码查看器 — 嵌入浏览器与控制台之间，支持语法高亮
"""
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QTextEdit, QFileDialog, QTreeWidget, QTreeWidgetItem, QSplitter,
    QLineEdit, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect, QSize
from PyQt6.QtGui import QShortcut, QKeySequence, QPainter, QTextFormat
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class GenericHighlighter(QSyntaxHighlighter):
    """多语言语法高亮器 - Dracula 配色"""

    _LANG_RULES = {}  # 类级缓存: lang -> [(pattern, format), ...]

    def __init__(self, parent=None, language='text'):
        super().__init__(parent)
        self._rules = self._get_rules(language)

    @classmethod
    def _get_rules(cls, lang):
        if lang in cls._LANG_RULES:
            return cls._LANG_RULES[lang]
        rules = []
        # === 颜色定义 ===
        def _fmt(fg, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(fg))
            if bold: f.setFontWeight(700)
            if italic: f.setFontItalic(True)
            return f
        KW = lambda: _fmt("#ff79c6", bold=True)
        STR = lambda: _fmt("#f1fa8c")
        CM = lambda: _fmt("#6272a4", italic=True)
        NUM = lambda: _fmt("#bd93f9")
        FN = lambda: _fmt("#50fa7b")
        CL = lambda: _fmt("#8be9fd", bold=True)
        TAG = lambda: _fmt("#ff79c6", bold=True)
        ATTR = lambda: _fmt("#50fa7b")
        PROP = lambda: _fmt("#8be9fd")

        if lang == 'python':
            for w in ["and","as","assert","async","await","break","class","continue","def",
                      "del","elif","else","except","finally","for","from","global","if",
                      "import","in","is","lambda","nonlocal","not","or","pass","raise",
                      "return","try","while","with","yield","True","False","None","self","super"]:
                rules.append((rf'\b{w}\b', KW()))
            for p in [r'"[^"\\]*(\\.[^"\\]*)*"', r"'[^'\\]*(\\.[^'\\]*)*'",
                      r'"""[^"]*"""', r"'''[^']*'''", r'f".*?"', r"f'.*?'",
                      r'f""".*?"""', r"f'''.*?'''"]:
                rules.append((p, STR()))
            rules.append((r'#.*$', CM()))
            rules.append((r'@\w+', FN()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))
            rules.append((r'\b([a-zA-Z_]\w*)\s*\(', FN()))
            rules.append((r'\b([A-Z][a-zA-Z0-9_]*)\b', CL()))

        elif lang == 'javascript' or lang == 'typescript':
            for w in ["async","await","break","case","catch","class","const","continue",
                      "debugger","default","delete","do","else","export","extends","finally",
                      "for","function","if","import","in","instanceof","let","new",
                      "of","return","super","switch","this","throw","try","typeof",
                      "var","void","while","with","yield","true","false","null","undefined"]:
                rules.append((rf'\b{w}\b', KW()))
            if lang == 'typescript':
                for w in ["interface","type","enum","namespace","module","declare","abstract",
                          "implements","private","protected","public","readonly","static"]:
                    rules.append((rf'\b{w}\b', KW()))
            for p in [r'"[^"\\]*(\\.[^"\\]*)*"', r"'[^'\\]*(\\.[^'\\]*)*'",
                      r'`[^`]*`']:
                rules.append((p, STR()))
            rules.append((r'//.*$', CM()))
            rules.append((r'/\*.*?\*/', CM()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))
            rules.append((r'\b([a-zA-Z_$]\w*)\s*\(', FN()))
            rules.append((r'\b([A-Z][a-zA-Z0-9_$]*)\b', CL()))

        elif lang == 'json':
            for p in [r'"[^"\\]*(\\.[^"\\]*)*"']:
                rules.append((p, STR()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))
            rules.append((r'\b(true|false|null)\b', KW()))

        elif lang in ('yaml','yml'):
            rules.append((r'^\s*[\w-]+:', PROP()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", STR()))
            rules.append((r'#.*$', CM()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))
            rules.append((r'\b(true|false|null|yes|no|on|off)\b', KW()))

        elif lang in ('html','xml'):
            rules.append((r'<[!/?]?[\w-]+', TAG()))
            rules.append((r'[\w-]+(?==)', ATTR()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", STR()))
            rules.append((r'<!--.*?-->', CM()))

        elif lang == 'css':
            rules.append((r'[.#@][\w-]+', CL()))
            rules.append((r'[\w-]+(?=:)', PROP()))
            rules.append((r':\s*[^;]+', STR()))
            rules.append((r'\b\d+\.?\d*(px|em|rem|%|vh|vw|s|ms)?\b', NUM()))
            rules.append((r'/\*.*?\*/', CM()))
            rules.append((r'\b(important|url|none|auto|inherit|initial|unset|block|inline|flex|grid|absolute|relative|fixed)\b', KW()))

        elif lang in ('c','cpp','h','java','kt','swift','go','rs'):
            kw = ["if","else","for","while","do","switch","case","break","continue",
                  "return","class","struct","enum","interface","extends","implements",
                  "new","this","super","try","catch","finally","throw","throws",
                  "public","private","protected","static","final","abstract","void",
                  "int","long","float","double","char","boolean","byte","short",
                  "true","false","null","package","import","const","let","var","func",
                  "fn","mut","unsafe","type","val","fun","object","when","sealed",
                  "data","companion","suspend","inline","operator","init","where",
                  "defer","go","chan","map","range","select","goto"]
            for w in kw:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", STR()))
            rules.append((r'//.*$', CM()))
            rules.append((r'/\*.*?\*/', CM()))
            rules.append((r'\b\d+\.?\d*[fL]?\b', NUM()))
            rules.append((r'\b([a-zA-Z_]\w*)\s*\(', FN()))
            rules.append((r'\b([A-Z][a-zA-Z0-9_]*)\b', CL()))

        elif lang in ('sh','bat'):
            rules.append((r'#.*$', CM()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", STR()))
            for w in ["if","then","else","elif","fi","for","while","do","done",
                      "case","esac","in","function","return","exit","export","local",
                      "echo","set","unset","source","alias","break","continue",
                      "cd","ls","mkdir","rm","cp","mv","chmod","chown","grep",
                      "awk","sed","curl","wget","git","npm","pip","python","node"]:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))

        elif lang in ('ini','cfg','toml'):
            rules.append((r'^\s*\[.*?\]', TAG()))
            rules.append((r'^\s*[\w.-]+(?=\s*=)', PROP()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", STR()))
            rules.append((r'#.*$', CM()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))
            rules.append((r'\b(true|false|null)\b', KW()))

        elif lang == 'markdown':
            rules.append((r'^#{1,6}\s.*$', CL()))
            rules.append((r'\*\*.*?\*\*', PROP()))
            rules.append((r'`[^`]+`', STR()))
            rules.append((r'\[.*?\]\(.*?\)', ATTR()))
            rules.append((r'^[-*+]\s', FN()))
            rules.append((r'^>\s.*$', CM()))


        elif lang == "sql":
            sql_kw = ["select","from","where","insert","update","delete",
                      "create","alter","drop","table","index","view",
                      "join","inner","left","right","outer","on","and",
                      "or","not","null","is","in","like","between",
                      "order","by","group","having","asc","desc","limit",
                      "offset","union","all","distinct","as","set",
                      "primary","key","foreign","references","constraint",
                      "default","values","into","exists","case","when",
                      "then","else","end","begin","commit","rollback"]
            for w in sql_kw:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", STR()))
            rules.append((r'--.*$', CM()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))

        elif lang == "vue":
            rules.append((r'<[!/?]?[\w-]+', TAG()))
            rules.append((r'[\w-]+(?==)', ATTR()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r'<!--.*?-->', CM()))
            rules.append((r'\{\{.*?\}\}', FN()))
            vue_kw = ["export","default","import","from","const","let",
                      "var","function","return","if","else","for",
                      "this","new","true","false","null"]
            for w in vue_kw:
                rules.append((rf'\b{w}\b', KW()))

        elif lang == "ruby":
            rb_kw = ["def","end","class","module","if","else","elsif",
                     "unless","while","until","for","do","begin",
                     "rescue","ensure","return","yield","self","super",
                     "true","false","nil","and","or","not",
                     "require","include","extend","attr_accessor"]
            for w in rb_kw:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", STR()))
            rules.append((r'#.*$', CM()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))
            rules.append((r'\b([a-z_]\w*)\s*\(', FN()))
            rules.append((r'\b([A-Z][a-zA-Z0-9_]*)\b', CL()))

        elif lang == "php":
            php_kw = ["echo","print","return","if","else","elseif",
                      "while","for","foreach","function","class",
                      "public","private","protected","static","new",
                      "this","extends","implements","namespace","use",
                      "require","include","true","false","null",
                      "try","catch","finally","throw"]
            for w in php_kw:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", STR()))
            rules.append((r'//.*$', CM()))
            rules.append((r'/\*.*?\*/', CM()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))
            rules.append((r'\$[a-zA-Z_]\w*', PROP()))

        elif lang == "csharp":
            cs_kw = ["using","namespace","class","struct","interface",
                     "public","private","protected","internal","static",
                     "void","int","string","bool","double","float",
                     "var","new","return","if","else","for","foreach",
                     "while","do","switch","case","break","continue",
                     "try","catch","finally","throw","async","await",
                     "true","false","null","this","base","virtual",
                     "override","abstract","sealed","readonly","const"]
            for w in cs_kw:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r'//.*$', CM()))
            rules.append((r'/\*.*?\*/', CM()))
            rules.append((r'\b\d+\.?\d*[fLm]?\b', NUM()))
            rules.append((r'\b([A-Z][a-zA-Z0-9_]*)\b', CL()))

        elif lang == "dart":
            dart_kw = ["class","extends","implements","with","import",
                       "export","void","int","double","String","bool",
                       "var","final","const","static","new","return",
                       "if","else","for","while","do","switch",
                       "case","break","continue","try","catch","finally",
                       "throw","async","await","true","false","null"]
            for w in dart_kw:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r'//.*$', CM()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))
            rules.append((r'\b([a-zA-Z_]\w*)\s*\(', FN()))
            rules.append((r'\b([A-Z][a-zA-Z0-9_]*)\b', CL()))

        elif lang == "lua":
            lua_kw = ["function","end","if","then","else","elseif",
                      "for","while","do","repeat","until","return",
                      "local","nil","true","false","and","or","not",
                      "break","goto"]
            for w in lua_kw:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r'--.*$', CM()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))

        elif lang == "r":
            r_kw = ["function","if","else","for","while","repeat",
                    "return","library","require","TRUE","FALSE","NULL",
                    "NA","Inf","NaN","in","next","break"]
            for w in r_kw:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r'#.*$', CM()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))
            rules.append((r'\b([a-zA-Z.]\w*)\s*<-', FN()))

        elif lang == "elixir":
            ex_kw = ["def","defp","defmodule","defstruct","do","end",
                     "if","else","unless","case","cond","for",
                     "fn","true","false","nil","when","and","or",
                     "not","import","alias","require","use","raise",
                     "rescue","try","catch","after","throw"]
            for w in ex_kw:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))
            rules.append((r'#.*$', CM()))
            rules.append((r'\b\d+\.?\d*\b', NUM()))
            rules.append((r'\b:[a-z_]\w*', ATTR()))

        elif lang == "dockerfile":
            df_kw = ["FROM","RUN","CMD","ENTRYPOINT","COPY","ADD",
                     "WORKDIR","ENV","ARG","EXPOSE","VOLUME","LABEL",
                     "USER","HEALTHCHECK","ONBUILD","STOPSIGNAL","SHELL"]
            for w in df_kw:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'#.*$', CM()))
            rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STR()))

        elif lang == "makefile":
            rules.append((r'#.*$', CM()))
            rules.append((r'^\s*[\w.-]+\s*[:+!?]=', PROP()))
            mf_kw = ["ifneq","ifeq","else","endif","include","export","define","endef"]
            for w in mf_kw:
                rules.append((rf'\b{w}\b', KW()))
            rules.append((r'\$\([^)]+\)', ATTR()))

        elif lang == "text":
            pass
        cls._LANG_RULES[lang] = rules
        return rules

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for m in re.finditer(pattern, text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class LineNumberArea(QWidget):
    """行号侧边栏"""
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint(event)


class CodeEditor(QPlainTextEdit):
    """带行号的代码编辑器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_line_number_area_width(0)
        self._highlight_current_line()

    def line_number_area_width(self):
        digits = max(3, len(str(self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def _update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#0d1117"))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber() + 1
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number)
                painter.setPen(QColor("#484f58"))
                painter.setFont(QFont("Consolas", 10))
                painter.drawText(0, int(top), self._line_number_area.width() - 4,
                                 self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def _highlight_current_line(self):
        """高亮当前行，同时保留搜索高亮（黄色背景/下划线）"""
        existing = self.extraSelections()
        search_sel = []
        for s in existing:
            try:
                bg = s.format.background().color().name()
                ul = s.format.underlineStyle()
                if bg in ("#fbbf24", "#fbbf2433") or ul != QTextFormat.UnderlineStyle.NoUnderline:
                    search_sel.append(s)
            except Exception:
                search_sel.append(s)
        extra_selections = list(search_sel)
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#1e3a5f"))
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)


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
        # 上下导航（搜索匹配结果切换）
        for text, slot, tip in [("▲ 上一个", self._prev_match, "上一个匹配结果"),
                                ("▼ 下一个", self._next_match, "下一个匹配结果")]:
            btn_nav = QPushButton(text)
            btn_nav.setFixedSize(74, 24)
            btn_nav.setToolTip(tip)
            btn_nav.clicked.connect(slot)
            btn_nav.setStyleSheet("background:#334155;color:#e2e8f0;border:none;border-radius:3px;font-size:11px;padding:0 2px;")
            btn_nav.setCursor(Qt.CursorShape.PointingHandCursor)
            tb.addWidget(btn_nav)
        for text, color, slot in [("💾 保存", "#f59e0b", self._save_file),
                                   ("📂 打开", "#10b981", self._open_dialog),
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
        self._editor = CodeEditor()
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
        QShortcut(QKeySequence("Ctrl+S"), self, self._save_file)
        QShortcut(QKeySequence("Escape"), self, self._clear_search)

    def _lbl(self, text, color, size, bold=False):
        w = "bold;" if bold else ""
        l = QLabel(text); l.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{w}")
        return l

    def _detect_language(self, path):
        """根据文件扩展名返回语言标识"""
        ext = path.suffix.lower()
        lang_map = {
            '.py': 'python', '.pyw': 'python', '.pyx': 'python', '.pxd': 'python',
            '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
            '.ts': 'typescript', '.tsx': 'typescript', '.jsx': 'javascript',
            '.json': 'json', '.jsonc': 'json',
            '.yaml': 'yaml', '.yml': 'yml',
            '.html': 'html', '.htm': 'html', '.xhtml': 'html',
            '.xml': 'xml', '.svg': 'xml', '.wsdl': 'xml', '.xsd': 'xml',
            '.css': 'css', '.scss': 'css', '.less': 'css',
            '.c': 'c', '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
            '.h': 'h', '.hpp': 'h', '.hh': 'h', '.hxx': 'h',
            '.java': 'java',
            '.kt': 'kt', '.kts': 'kt', '.ktm': 'kt',
            '.swift': 'swift',
            '.go': 'go',
            '.rs': 'rs',
            '.sh': 'sh', '.bash': 'sh', '.zsh': 'sh', '.fish': 'sh',
            '.bat': 'bat', '.cmd': 'bat', '.ps1': 'bat',
            '.ini': 'ini', '.cfg': 'cfg', '.conf': 'cfg', '.cnf': 'cfg',
            '.toml': 'toml',
            '.md': 'markdown', '.markdown': 'markdown', '.rst': 'markdown',
            '.sql': 'sql', '.psql': 'sql',
            '.vue': 'vue',
            '.rb': 'ruby', '.rake': 'ruby', '.gemspec': 'ruby',
            '.php': 'php', '.phtml': 'php', '.php3': 'php', '.php4': 'php',
            '.cs': 'csharp',
            '.dart': 'dart',
            '.lua': 'lua',
            '.r': 'r',
            '.ex': 'elixir', '.exs': 'elixir', '.eex': 'elixir',
            '.txt': 'text', '.text': 'text', '.log': 'text',
            '.env': 'ini',
        }
        if ext in lang_map:
            return lang_map[ext]
        name = path.name.lower()
        if name == 'dockerfile' or name.startswith('dockerfile.'):
            return 'dockerfile'
        if name in ('makefile', 'gnumakefile', 'makefile.in'):
            return 'makefile'
        if name in ('.gitignore', '.dockerignore', '.editorconfig'):
            return 'ini'
        if name in ('license', 'changelog', 'readme', 'authors', 'contributing',
                     'notice', 'code_of_conduct', 'security'):
            return 'text'
        return None

    def _refresh_tree(self):
        try:
            self._tree.clear()
            self._add_dir(PROJECT_ROOT, self._tree.invisibleRootItem())
            self._tree.expandToDepth(1)
            count = self._tree.topLevelItemCount()
            self._status.setText(f"🔄 已刷新 — {count} 个顶级目录")
        except Exception as e:
            self._status.setText(f"❌ 刷新失败: {e}")

    def _add_dir(self, path, parent):
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            for i, e in enumerate(entries):
                if i >= 60 or (e.name.startswith('.') and e.name not in ('.env','.gitignore','.dockerignore','.editorconfig','.htaccess')):
                    continue
                if e.name in ('__pycache__','node_modules','.git','dist','build','.venv','venv','.idea','.vscode','egg-info'):
                    continue
                if e.is_dir():
                    node = QTreeWidgetItem(parent, [f"📁 {e.name}"])
                    node.setData(0, Qt.ItemDataRole.UserRole, str(e))
                    node.setData(0, Qt.ItemDataRole.UserRole + 1, True)
                    if parent is self._tree.invisibleRootItem():
                        self._add_dir(e, node)
                elif e.suffix in ('.py','.pyw','.pyx','.pxd','.json','.jsonc','.yaml','.yml','.txt','.md','.rst','.html','.htm','.xhtml','.css','.scss','.less',
                                   '.js','.mjs','.cjs','.jsx','.ts','.tsx','.toml','.cfg','.conf','.cnf','.ini','.bat','.cmd','.ps1','.sh','.bash','.zsh','.fish','.xml','.svg','.wsdl','.xsd',
                                   '.kt','.kts','.ktm','.java','.swift','.c','.cpp','.cc','.cxx','.h','.hpp','.hh','.hxx','.rs','.go',
                                   '.sql','.psql','.vue','.rb','.rake','.gemspec','.php','.phtml','.cs','.dart','.lua','.r','.ex','.exs','.eex'):
                    ico = {'py':'🐍','pyw':'🐍','pyx':'🐍','pxd':'🐍','json':'📋','jsonc':'📋','yaml':'⚙️','yml':'⚙️','txt':'📄','md':'📝','rst':'📝',
                           'html':'🌐','htm':'🌐','xhtml':'🌐','css':'🎨','scss':'🎨','less':'🎨','js':'📜','mjs':'📜','cjs':'📜','jsx':'📜','ts':'📘','tsx':'📘',
                           'toml':'⚙️','cfg':'⚙️','conf':'⚙️','cnf':'⚙️','ini':'⚙️','bat':'⚡','cmd':'⚡','ps1':'⚡','sh':'🐚','bash':'🐚','zsh':'🐚','fish':'🐚',
                           'xml':'📋','svg':'📋','wsdl':'📋','xsd':'📋','kt':'🅱️','kts':'🅱️','java':'☕','swift':'🦅',
                           'c':'⚙️','cpp':'⚙️','cc':'⚙️','cxx':'⚙️','h':'⚙️','hpp':'⚙️','hh':'⚙️','hxx':'⚙️','rs':'🦀','go':'🐹',
                           'sql':'🗄️','psql':'🗄️','vue':'💚','rb':'💎','rake':'💎','gemspec':'💎','php':'🐘','phtml':'🐘','cs':'🟣','dart':'🎯','lua':'🌙','r':'📊','ex':'🧪','exs':'🧪','eex':'🧪'}.get(e.suffix,'📄')
                    node = QTreeWidgetItem(parent, [f"{ico} {e.name}"])
                    node.setData(0, Qt.ItemDataRole.UserRole, str(e))
                    node.setData(0, Qt.ItemDataRole.UserRole + 1, False)
                elif e.is_file() and e.suffix == '' and e.name.lower() in (
                    'dockerfile','makefile','gnumakefile','license','changelog',
                    'readme','authors','contributing','notice','code_of_conduct','security'):
                    ico2 = {'dockerfile':'🐳','makefile':'🔧','gnumakefile':'🔧','license':'⚖️',
                            'changelog':'📝','readme':'📖','authors':'👥','contributing':'🤝',
                            'notice':'📢','code_of_conduct':'📜','security':'🔒'}.get(e.name.lower(),'📄')
                    node = QTreeWidgetItem(parent, [f"{ico2} {e.name}"])
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

    def _read_file_smart(self, path: Path) -> str:
        """智能读取文件：自动检测编码 UTF-8 -> GBK -> Latin-1"""
        raw = path.read_bytes()
        if raw[:3] == b'\xef\xbb\xbf':
            raw = raw[3:]
        for enc in ('utf-8', 'gbk', 'gb2312', 'latin-1'):
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode('utf-8', errors='replace')

    def open_file(self, path):
        try:
            p = Path(path)
            if not p.exists():
                self._status.setText(f"❌ 文件不存在: {path}")
                return
            content = self._read_file_smart(p)
            self._editor.setPlainText(content)
            if self._highlighter:
                self._highlighter.deleteLater(); self._highlighter = None
            lang = self._detect_language(p)
            if lang:
                self._highlighter = GenericHighlighter(self._editor.document(), language=lang)
            self._current_file = str(p); self._file_label.setText(p.name)
            rel = p.relative_to(PROJECT_ROOT) if str(p).startswith(str(PROJECT_ROOT)) else p
            self._status.setText(f"✅ {rel} — {len(content)} 字符, {content.count(chr(10))+1} 行")
            self.file_selected.emit(str(p))
            self._highlight_in_tree(str(p))
        except Exception as e:
            self._status.setText(f"❌ 打开失败: {e}")

    def _save_file(self):
        """保存当前文件"""
        if not self._current_file:
            self._status.setText("⚠️ 没有打开文件，无法保存")
            return
        try:
            content = self._editor.toPlainText()
            p = Path(self._current_file)
            p.write_text(content, encoding='utf-8')
            self._status.setText(f"💾 已保存: {p.name} — {len(content)} 字符, {content.count(chr(10)) + 1} 行")
        except Exception as e:
            self._status.setText(f"❌ 保存失败: {e}")
            QMessageBox.critical(self, "保存失败", f"无法保存文件:\n{e}")

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
                    '.py','.pyw','.pyx','.pxd','.json','.jsonc','.yaml','.yml','.txt','.md','.rst','.html','.htm','.xhtml','.css','.scss','.less',
                    '.js','.mjs','.cjs','.jsx','.ts','.tsx','.toml','.cfg','.conf','.cnf','.ini','.bat','.cmd','.ps1','.sh','.bash','.zsh','.fish','.xml','.svg','.wsdl','.xsd',
                    '.kt','.kts','.ktm','.java','.swift','.c','.cpp','.cc','.cxx','.h','.hpp','.hh','.hxx','.rs','.go',
                    '.sql','.psql','.vue','.rb','.rake','.gemspec','.php','.phtml','.cs','.dart','.lua','.r','.ex','.exs','.eex'):
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
                elif e.is_file() and e.suffix == '' and e.name.lower() in (
                    'dockerfile','makefile','gnumakefile','license','changelog',
                    'readme','authors','contributing','notice','code_of_conduct','security'):
                    ico2 = {'dockerfile':'🐳','makefile':'🔧','gnumakefile':'🔧','license':'⚖️',
                            'changelog':'📝','readme':'📖','authors':'👥','contributing':'🤝',
                            'notice':'📢','code_of_conduct':'📜','security':'🔒'}.get(e.name.lower(),'📄')
                    node = QTreeWidgetItem(parent, [f"{ico2} {e.name}"])
                    node.setData(0, Qt.ItemDataRole.UserRole, str(e))
                    node.setData(0, Qt.ItemDataRole.UserRole + 1, False)
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
            # 搜索高亮（合并当前行高亮）
            from PyQt6.QtGui import QTextCharFormat
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor("#fbbf2433"))
            sel.format.setUnderlineStyle(
                QTextCharFormat.UnderlineStyle.SingleUnderline
            )
            sel.format.setUnderlineColor(QColor("#fbbf24"))
            sel.cursor = cursor
            # 合并当前行高亮，不覆盖
            current = self._editor.extraSelections()
            current.append(sel)
            self._editor.setExtraSelections(current)

    def _clear_search_highlight(self):
        """清除搜索高亮，恢复当前行高亮"""
        self._editor.setExtraSelections([])
        self._editor._highlight_current_line()

    def show_file(self, path):
        self.open_file(path)
