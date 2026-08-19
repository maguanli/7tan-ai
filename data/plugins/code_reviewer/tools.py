
"""
代码质量审查插件 — 静态分析、安全检查、代码规范
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

import os
import re
import ast
import json
from pathlib import Path

@register_tool(
    name="code_review_file",
    description="对单个代码文件进行静态分析和质量审查，检查常见问题",
    parameters={"file_path": {"type": "string", "description": "文件完整路径"}},
    category="dev"
)
def code_review_file(file_path: str) -> dict:
    """审查单个文件，检查常见问题"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    issues = []
    ext = Path(file_path).suffix.lower()
    
    # Python 文件用 AST 分析
    if ext == ".py":
        issues += _review_python(content, file_path)
    
    # 通用检查
    issues += _review_generic(content, file_path, ext)
    
    return {
        "success": True,
        "file": file_path,
        "language": ext,
        "lines": len(content.split("\n")),
        "issues_count": len(issues),
        "issues": issues,
        "severity": {
            "critical": sum(1 for i in issues if i["severity"] == "critical"),
            "warning": sum(1 for i in issues if i["severity"] == "warning"),
            "info": sum(1 for i in issues if i["severity"] == "info")
        }
    }

@register_tool(
    name="code_review_directory",
    description="对目录中的所有代码文件进行批量审查",
    parameters={"dir_path": {"type": "string", "description": "目录路径"}, "extensions": {"type": "string", "description": "文件扩展名，逗号分隔", "default": ".py,.java,.kt,.swift,.js,.ts"}},
    category="dev"
)
def code_review_directory(dir_path: str, extensions: str = ".py,.java,.kt,.swift,.js,.ts") -> dict:
    """批量审查目录下所有代码文件"""
    exts = extensions.split(",")
    results = []
    
    for root, dirs, files in os.walk(dir_path):
        # 跳过隐藏目录和常见忽略目录
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in 
                   ("node_modules", "__pycache__", ".git", "build", "dist", ".gradle")]
        for f in files:
            if any(f.endswith(ext) for ext in exts):
                file_path = os.path.join(root, f)
                result = code_review_file(file_path)
                if result["success"] and result["issues_count"] > 0:
                    results.append(result)
    
    total_issues = sum(r["issues_count"] for r in results)
    return {
        "success": True,
        "directory": dir_path,
        "files_scanned": len(results),
        "total_issues": total_issues,
        "results": results[:50]  # 最多返回50个文件
    }

@register_tool(
    name="security_scan_file",
    description="对文件进行安全扫描，检测漏洞和风险代码",
    parameters={"file_path": {"type": "string", "description": "文件路径"}},
    category="dev"
)
def security_scan_file(file_path: str) -> dict:
    """安全扫描：检查硬编码密码、API密钥、SQL注入等"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    vulnerabilities = []
    
    # 硬编码密码模式
    password_patterns = [
        (r'(?:password|passwd|pwd|secret|token|api_key|apikey)\s*[:=]\s*["\']([^"\']{4,})["\']', "硬编码密钥/密码"),
        (r'(?:private_key|private key)', "私钥引用"),
        (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
        (r'sk-[a-zA-Z0-9]{32,}', "OpenAI API Key"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub Token"),
    ]
    
    for pattern, desc in password_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            vulnerabilities.append({
                "type": "hardcoded_secret",
                "description": desc,
                "count": len(matches),
                "severity": "critical"
            })
    
    # SQL 注入风险
    sql_patterns = [
        (r'(?:execute|cursor\.execute)\s*\(\s*f["\']', "可能的 SQL 注入 (f-string)"),
        (r'(?:execute|cursor\.execute)\s*\(\s*["\'].*%s.*["\'].*%', "可能的 SQL 注入 (% 格式化)"),
    ]
    
    for pattern, desc in sql_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            vulnerabilities.append({
                "type": "sql_injection",
                "description": desc,
                "severity": "warning"
            })
    
    return {
        "success": True,
        "file": file_path,
        "vulnerabilities_count": len(vulnerabilities),
        "vulnerabilities": vulnerabilities
    }

@register_tool(
    name="code_stats",
    description="统计目录中代码文件的行数、函数数等基本信息",
    parameters={"dir_path": {"type": "string", "description": "目录路径"}},
    category="dev"
)
def code_stats(dir_path: str) -> dict:
    """统计代码量"""
    stats = {"total_lines": 0, "total_files": 0, "by_language": {}}
    
    ext_map = {
        ".py": "Python", ".java": "Java", ".kt": "Kotlin",
        ".swift": "Swift", ".js": "JavaScript", ".ts": "TypeScript",
        ".php": "PHP", ".html": "HTML", ".css": "CSS",
        ".xml": "XML", ".json": "JSON", ".yaml": "YAML",
        ".gradle": "Gradle", ".sh": "Shell", ".bat": "Batch",
        ".c": "C", ".cpp": "C++", ".h": "C/C++ Header"
    }
    
    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in 
                   ("node_modules", "__pycache__", ".git", "build", "dist")]
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in ext_map:
                lang = ext_map[ext]
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                        lines = len(fh.readlines())
                    stats["total_lines"] += lines
                    stats["total_files"] += 1
                    stats["by_language"][lang] = stats["by_language"].get(lang, 0) + lines
                except:
                    pass
    
    return {"success": True, "stats": stats}

def _review_python(content: str, file_path: str) -> list:
    """Python 代码审查"""
    issues = []
    lines = content.split("\n")
    
    # AST 分析
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({"line": node.lineno, "severity": "warning", 
                             "message": "裸 except（应指定异常类型）"})
    except SyntaxError as e:
        issues.append({"line": e.lineno, "severity": "critical", 
                     "message": f"语法错误: {e.msg}"})
    
    # 逐行检查
    for i, line in enumerate(lines, 1):
        if len(line) > 150:
            issues.append({"line": i, "severity": "info", "message": "行过长 (>150字符)"})
        if re.search(r'\bprint\s*\(', line) and not file_path.endswith("__main__"):
            issues.append({"line": i, "severity": "info", "message": "残留 print 调试语句"})
    
    return issues

def _review_generic(content: str, file_path: str, ext: str) -> list:
    """通用代码审查"""
    issues = []
    lines = content.split("\n")
    
    for i, line in enumerate(lines, 1):
        # TODO/FIXME 注释
        if re.search(r'(?:TODO|FIXME|HACK|XXX)', line):
            issues.append({"line": i, "severity": "info", "message": f"待办标记: {line.strip()}"})
        # 制表符检查（非 Makefile）
        if "\t" in line and ext not in (".mk",):
            issues.append({"line": i, "severity": "info", "message": "使用制表符缩进（建议用空格）"})
    
    # 文件末尾空行
    if content and not content.endswith("\n"):
        issues.append({"line": len(lines), "severity": "info", "message": "文件末尾缺少换行"})
    
    return issues
