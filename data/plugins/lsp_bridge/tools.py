"""
LSP 桥接插件 — 跳转定义、查找引用、诊断检查、代码补全

基于 jedi (Python AST) + pyflakes (诊断) 的双引擎实现。
纯 Python 实现，无需额外安装 LSP 服务器。
非 Python 语言回退到正则文本搜索。
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import os


def _find_neo4():
    """查找 jedi 库是否可用"""
    try:
        import jedi
        return True
    except ImportError:
        return False


def _find_pyflakes():
    try:
        import pyflakes.api
        return True
    except ImportError:
        return False


# ===================== 跳转定义 =====================

def _safe_column(line_count: int, line: int, column: int) -> int:
    """计算 jedi 安全列号（jedi 列号从0开始），防止空行越界"""
    if line > line_count:
        return 0
    jedi_col = max(0, column - 1)
    return jedi_col


@register_tool(
    name="go_to_definition",
    description="跳转到符号（函数/类/变量）的定义位置。输入文件路径、行号、列号，返回定义所在的文件和位置。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "源文件路径"},
            "line": {"type": "integer", "description": "光标所在行号（从1开始）"},
            "column": {"type": "integer", "description": "光标所在列号（从1开始）", "default": 1},
        },
        "required": ["file_path", "line"]
    },
    category="lsp"
)
def go_to_definition(file_path: str, line: int, column: int = 1) -> str:
    """跳转到定义"""
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"

    ext = os.path.splitext(file_path)[1].lower()

    # Python: 使用 jedi
    if ext == ".py" and _find_neo4():
        import jedi
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            source = "".join(lines)
            script = jedi.Script(source, path=file_path)
            jedi_col = _safe_column(len(lines), line, column)
            names = script.goto(line=line, column=jedi_col)
            if not names:
                return f"未找到定义 (文件: {file_path}, 行: {line}, 列: {column})"

            results = []
            for n in names:
                def_path = n.module_path or file_path
                def_line = n.line or "?"
                def_col = n.column or "?"
                results.append(
                    f"📍 {n.full_name or n.name}\n"
                    f"   类型: {n.type}\n"
                    f"   位置: {def_path}:{def_line}:{def_col}"
                )
                if n.docstring():
                    brief = n.docstring().split("\n")[0][:100]
                    results[-1] += f"\n   Doc: {brief}"
            return "\n\n".join(results)
        except Exception as e:
            return f"jedi 分析失败: {e}"

    # JavaScript/TypeScript: 使用正则分析
    if ext in (".js", ".ts", ".jsx", ".tsx", ".mjs"):
        return _js_ts_definition(file_path, line)

    # 非 Python: 回退到文本搜索
    return _text_based_definition(file_path, line, ext)


def _js_ts_definition(file_path: str, line: int) -> str:
    """JS/TS 定义查找"""
    import re
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if line > len(lines):
            return f"行号超出范围 (文件共 {len(lines)} 行)"

        target = lines[line - 1]
        # 提取符号名
        symbol = None
        for p in [
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)',
            r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*[:=]\s*(?:async\s*)?\(',
            r'(?:export\s+)?class\s+(\w+)',
            r'(\w+)\(',
            r'(?:import\s+.*\b)(\w+)',
        ]:
            m = re.search(p, target)
            if m:
                symbol = m.group(1)
                break
        if not symbol:
            return f"无法识别符号: {target.strip()[:80]}"

        # 在项目中搜索定义
        found = []
        def_patterns = [
            f"function {symbol}", f"const {symbol}", f"let {symbol}",
            f"class {symbol}", f"export function {symbol}",
            f"export const {symbol}", f"export class {symbol}",
        ]
        for root, dirs, files in os.walk(os.path.dirname(file_path)):
            dirs[:] = [d for d in dirs if d not in
                       ("node_modules", ".git", "dist", "build")]
            for fname in files:
                if not fname.endswith((".js", ".ts", ".jsx", ".tsx", ".mjs")):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as fp:
                        for i, l in enumerate(fp, 1):
                            for dp in def_patterns:
                                if dp in l:
                                    found.append(f"📍 {fpath}:{i}: {l.strip()[:120]}")
                                    if len(found) >= 10:
                                        break
                            if len(found) >= 10:
                                break
                    if len(found) >= 10:
                        break
                except Exception:
                    pass
            if len(found) >= 10:
                break
        if not found:
            return f"未找到 '{symbol}' 的定义"
        return f"🔍 JS/TS 定义搜索 '{symbol}':\n" + "\n".join(found)
    except Exception as e:
        return f"搜索失败: {e}"


def _text_based_definition(file_path: str, line: int, ext: str) -> str:
    """文本搜索回退"""
    import re
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if line > len(lines):
            return f"行号超出范围 (文件共 {len(lines)} 行)"

        target_line = lines[line - 1]
        # 提取当前行中的符号名
        symbol = None
        patterns = [
            # def/class/async def 后的名称
            r'\b(?:def|class|async\s+def)\s+(\w+)',
            # 函数调用
            r'(\w+)\(',
            # import 后的名称
            r'(?:from\s+\S+\s+import\s+|import\s+)(\w+)',
            # 赋值左侧
            r'(\w+)\s*=',
        ]
        for p in patterns:
            m = re.search(p, target_line)
            if m:
                symbol = m.group(1)
                break

        if not symbol:
            return f"无法识别行 {line} 中的符号: {target_line.strip()[:80]}"

        # 在项目中搜索定义
        project_dir = os.path.dirname(file_path)
        found = []
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                       ("node_modules", "__pycache__", ".git", "venv", ".venv")]
            for fname in files:
                if not fname.endswith(ext):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as fp:
                        for i, l in enumerate(fp, 1):
                            if f"def {symbol}" in l or f"class {symbol}" in l:
                                found.append(f"📍 {fpath}:{i}: {l.strip()[:100]}")
                                if len(found) >= 5:
                                    break
                    if len(found) >= 5:
                        break
                except Exception:
                    pass
            if len(found) >= 5:
                break

        if not found:
            return f"文本搜索未找到 '{symbol}' 的定义"
        return f"🔍 文本搜索 '{symbol}':\n" + "\n".join(found)
    except Exception as e:
        return f"搜索失败: {e}"


# ===================== 查找引用 =====================

@register_tool(
    name="find_all_references",
    description="查找指定文件中某个符号（函数/类/变量）在项目中的所有引用位置。支持 Python jedi 语义分析和文本回退。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "源文件路径"},
            "line": {"type": "integer", "description": "符号所在行号"},
            "column": {"type": "integer", "description": "符号所在列号", "default": 1},
            "max_results": {"type": "integer", "description": "最大结果数", "default": 50},
        },
        "required": ["file_path", "line"]
    },
    category="lsp"
)
def find_all_references(file_path: str, line: int, column: int = 1,
                        max_results: int = 50) -> str:
    """查找所有引用"""
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".py" and _find_neo4():
        import jedi
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                source = "".join(lines)
            script = jedi.Script(source, path=file_path)
            jedi_col = _safe_column(len(lines), line, column)
            names = script.get_references(line=line, column=jedi_col)

            if not names:
                return f"未找到引用 (文件: {file_path}, 行: {line})"

            results = [f"📎 找到 {len(names)} 处引用:"]
            for n in names:
                ref_path = n.module_path or file_path
                ref_line = n.line
                try:
                    with open(ref_path, "r", encoding="utf-8") as fp:
                        ref_lines = fp.readlines()
                    if ref_line and ref_line <= len(ref_lines):
                        ctx = ref_lines[ref_line - 1].strip()[:120]
                    else:
                        ctx = "(行号?)"
                except Exception:
                    ctx = "(无法读取)"
                results.append(f"  {ref_path}:{ref_line}: {ctx}")
            return "\n".join(results[:max_results + 1])
        except Exception as e:
            return f"jedi 分析失败: {e}"

    # 回退：提取符号名，grep 搜索
    import re
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        target = lines[line - 1].strip()
        # 提取符号名
        for p in [r'\b(?:def|class|async\s+def)\s+(\w+)', r'(\w+)\s*[=:(]']:
            m = re.search(p, target)
            if m:
                symbol = m.group(1)
                break
        else:
            return f"无法从 '{target[:60]}' 提取符号名"

        return _grep_symbol(symbol, os.path.dirname(file_path), max_results)
    except Exception as e:
        return f"搜索失败: {e}"


# ===================== 诊断检查 =====================

@register_tool(
    name="get_diagnostics",
    description="检查 Python 文件的语法错误、未使用导入、未定义变量等问题。类似 VS Code 的波浪线错误提示。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Python 文件路径"},
            "check_types": {"type": "string", "description": "检查类型: all/syntax/imports/variables", "default": "all"},
        },
        "required": ["file_path"]
    },
    category="lsp"
)
def get_diagnostics(file_path: str, check_types: str = "all") -> str:
    """诊断检查"""
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"
    if not file_path.endswith(".py"):
        return "⚠️ 诊断目前仅支持 Python 文件"

    results = []

    # 1. 语法检查
    if check_types in ("all", "syntax"):
        import ast
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            ast.parse(source, filename=file_path)
            results.append("✅ 语法: 无错误")
        except SyntaxError as e:
            results.append(
                f"❌ 语法错误:\n"
                f"   位置: 行 {e.lineno}, 列 {e.offset}\n"
                f"   消息: {e.msg}\n"
                f"   代码: {e.text.strip() if e.text else ''}"
            )

    # 2. 导入和变量检查（pyflakes）
    if check_types in ("all", "imports", "variables") and _find_pyflakes():
        import io
        import pyflakes.api
        import pyflakes.reporter
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            warnings_out = io.StringIO()
            reporter = pyflakes.reporter.Reporter(warnings_out, warnings_out)
            pyflakes.api.check(source, file_path, reporter)
            warns = warnings_out.getvalue().strip()
            if warns:
                results.append(f"⚠️ 代码问题:\n{warns}")
            else:
                results.append("✅ 代码质量: 无问题")
        except Exception as e:
            results.append(f"⚠️ pyflakes 检查失败: {e}")

    # 3. 手动静态检查（补充 pyflakes 未覆盖的）
    if check_types in ("all",):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            manual = []
            for i, line in enumerate(lines, 1):
                s = line.strip()
                # 裸 except
                if s == "except:" or s == "except :":
                    manual.append(f"  行{i}: 裸 except（建议指定异常类型）")
                # print 调试
                if s.startswith("print(") and "print(__" not in s:
                    manual.append(f"  行{i}: 残留 print 调试语句")
                # 过长行
                if len(s) > 150:
                    manual.append(f"  行{i}: 代码行过长 ({len(s)}字符)")
                # TODO/FIXME
                if "TODO" in s or "FIXME" in s:
                    manual.append(f"  行{i}: {s[:80]}")
            if manual:
                results.append(f"💡 建议改进:\n" + "\n".join(manual[:20]))
        except Exception:
            pass

    return "\n\n".join(results)


# ===================== 补全建议 =====================

@register_tool(
    name="get_completions",
    description="获取光标位置的代码补全建议。支持 Python（jedi 语义补全），非 Python 回退到关键词匹配。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "源文件路径"},
            "line": {"type": "integer", "description": "光标所在行号"},
            "column": {"type": "integer", "description": "光标所在列号"},
            "prefix": {"type": "string", "description": "已输入的前缀文字（可选，用于文本回退）", "default": ""},
        },
        "required": ["file_path", "line", "column"]
    },
    category="lsp"
)
def get_completions(file_path: str, line: int, column: int,
                    prefix: str = "") -> str:
    """代码补全"""
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"

    if file_path.endswith(".py") and _find_neo4():
        import jedi
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            script = jedi.Script(source, path=file_path)
            completions = script.complete(line=line, column=column)

            if not completions:
                return "无补全建议"

            results = [f"💡 {len(completions)} 个补全建议:"]
            for c in completions[:15]:
                type_icon = {"function": "🔧", "class": "📦", "module": "📁",
                             "keyword": "🔑", "statement": "📝", "param": "⚙️",
                             "instance": "🔹"}.get(c.type, "•")
                desc = c.description[:60] if c.description else ""
                results.append(f"  {type_icon} {c.name:25s} {c.type:10s}  {desc}")
            return "\n".join(results)
        except Exception as e:
            return f"补全失败: {e}"

    # 非 Python 回退
    return f"⚠️ 补全仅支持 Python。当前文件: {os.path.basename(file_path)}"


# ===================== 文档悬停 =====================

@register_tool(
    name="get_hover_info",
    description="获取光标位置符号的文档信息（类似 VS Code 的悬停提示）。显示类型、文档字符串、参数列表。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "源文件路径"},
            "line": {"type": "integer", "description": "光标所在行号"},
            "column": {"type": "integer", "description": "光标所在列号", "default": 1},
        },
        "required": ["file_path", "line"]
    },
    category="lsp"
)
def get_hover_info(file_path: str, line: int, column: int = 1) -> str:
    """悬停文档"""
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"

    if file_path.endswith(".py") and _find_neo4():
        import jedi
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                source = "".join(lines)
            script = jedi.Script(source, path=file_path)
            jedi_col = _safe_column(len(lines), line, column)
            names = script.help(line=line, column=jedi_col)

            if not names:
                return "无文档信息"

            results = []
            for n in names[:3]:
                results.append(f"📖 {n.full_name or n.name}")
                results.append(f"   类型: {n.type}")
                if n.docstring():
                    doc = n.docstring().split("\n")[0][:200]
                    results.append(f"   文档: {doc}")
                if hasattr(n, 'params') and n.params:
                    results.append(f"   参数: {', '.join(str(p) for p in n.params)}")
            return "\n".join(results)
        except Exception as e:
            return f"jedi 分析失败: {e}"

    return "⚠️ 悬停文档仅支持 Python"


# ===================== 辅助函数 =====================

def _grep_symbol(symbol: str, directory: str, max_results: int = 50) -> str:
    """在目录中搜索符号引用"""
    import re
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("node_modules", "__pycache__", ".git", "venv", ".venv")]
        for fname in files:
            if not fname.endswith((".py", ".js", ".ts", ".go", ".rs", ".java")):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
                    for i, line in enumerate(fp, 1):
                        if pattern.search(line):
                            results.append(f"  {os.path.relpath(fpath, directory)}:{i}: {line.strip()[:120]}")
                            if len(results) >= max_results:
                                break
                if len(results) >= max_results:
                    break
            except Exception:
                pass
        if len(results) >= max_results:
            break
    if not results:
        return f"未找到对 '{symbol}' 的引用"
    return f"📎 找到 {len(results)} 处引用 ('{symbol}'):\n" + "\n".join(results)
