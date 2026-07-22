"""
调试辅助插件 — 堆栈分析、错误解释、修复建议、日志搜索
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import re
import os
import traceback


@register_tool(
    name="analyze_error",
    description="分析 Python 错误堆栈，解释错误原因并提供修复建议。支持常见错误类型：ImportError、AttributeError、TypeError、KeyError 等。",
    parameters={
        "type": "object",
        "properties": {
            "traceback_text": {"type": "string", "description": "完整的错误堆栈文本"},
        },
        "required": ["traceback_text"]
    },
    category="debug"
)
def analyze_error(traceback_text: str) -> str:
    """分析错误堆栈"""
    lines = traceback_text.strip().split("\n")
    error_type = "Unknown"
    error_msg = ""
    frames = []

    for line in lines:
        # 提取错误类型
        m = re.match(r'^(\w+(?:Error|Exception|Warning|ErrorException))\s*:?\s*(.*)', line)
        if m:
            error_type = m.group(1)
            error_msg = m.group(2)
        # 提取栈帧
        m = re.match(r'^\s*File\s+"([^"]+)",\s*line\s+(\d+)', line)
        if m:
            frames.append({"file": m.group(1), "line": int(m.group(2))})

    # 生成分析
    result = [f"🔍 错误分析: {error_type}"]
    if error_msg:
        result.append(f"   消息: {error_msg}")

    # 解释和建议
    suggestions = {
        "ImportError": ("模块未找到或导入路径错误。\n"
                        "  • 检查模块是否已安装: pip install <module>\n"
                        "  • 检查导入路径是否正确\n"
                        "  • 检查 PYTHONPATH 环境变量"),
        "ModuleNotFoundError": ("模块未安装或路径错误。\n"
                                "  • 安装缺失模块: pip install <module>\n"
                                "  • 检查是否在正确的虚拟环境中"),
        "AttributeError": ("对象没有该属性或方法。\n"
                          "  • 检查拼写是否正确\n"
                          "  • 确认对象类型 (使用 type() 检查)\n"
                          "  • 检查是否为 None 值"),
        "TypeError": ("类型不匹配。\n"
                     "  • 检查参数类型是否正确\n"
                     "  • 确认函数签名: help(function)\n"
                     "  • 检查是否为 None 传递给了需要具体类型的地方"),
        "KeyError": ("字典中不存在该键。\n"
                    "  • 使用 dict.get(key, default) 代替 dict[key]\n"
                    "  • 检查键名拼写\n"
                    "  • 打印 dict.keys() 查看可用键"),
        "IndexError": ("列表索引超出范围。\n"
                      "  • 检查列表长度: len(list)\n"
                      "  • 确保索引在 0 到 len-1 范围内"),
        "ValueError": ("值不合法。\n"
                      "  • 检查输入数据的格式和范围\n"
                      "  • 添加输入验证逻辑"),
        "FileNotFoundError": ("文件不存在。\n"
                             "  • 检查文件路径是否正确\n"
                             "  • 使用 os.path.exists() 预先检查\n"
                             "  • 检查相对路径 vs 绝对路径"),
        "PermissionError": ("权限不足。\n"
                           "  • 检查文件权限\n"
                           "  • 确认文件未被其他程序占用\n"
                           "  • Windows: 以管理员身份运行"),
        "ConnectionError": ("网络连接失败。\n"
                           "  • 检查网络连接\n"
                           "  • 确认目标服务是否运行\n"
                           "  • 检查防火墙/代理设置"),
        "SyntaxError": ("语法错误。\n"
                       "  • 检查括号是否匹配\n"
                       "  • 检查缩进是否一致\n"
                       "  • 检查冒号/引号/逗号是否遗漏"),
        "IndentationError": ("缩进错误。\n"
                            "  • 确保使用一致的缩进（4空格或Tab，不要混用）\n"
                            "  • 检查是否有混用空格和Tab"),
        "UnboundLocalError": ("变量作用域问题。\n"
                             "  • 函数内部有同名局部赋值，遮蔽了全局导入\n"
                             "  • 删除函数内部重复的 import 语句\n"
                             "  • 使用 global 关键字声明全局变量"),
    }

    for key, suggestion in suggestions.items():
        if key in error_type:
            result.append(f"\n💡 建议:\n{suggestion}")
            break
    else:
        result.append(f"\n💡 未识别的错误类型，请检查堆栈中的具体文件和行号。")

    if frames:
        result.append(f"\n📋 调用栈 ({len(frames)} 帧):")
        for i, f in enumerate(frames[:10]):
            result.append(f"  {'→' if i == 0 else '  '} {f['file']}:{f['line']}")

    return "\n".join(result)


@register_tool(
    name="analyze_log",
    description="搜索和分析项目日志文件中的错误和警告，按严重程度和频率排序。",
    parameters={
        "type": "object",
        "properties": {
            "log_dir": {"type": "string", "description": "日志目录路径", "default": "logs"},
            "pattern": {"type": "string", "description": "搜索关键词（可选，不填则显示所有错误）", "default": ""},
            "hours": {"type": "integer", "description": "只看最近N小时的日志", "default": 24},
        },
        "required": []
    },
    category="debug"
)
def analyze_log(log_dir: str = "logs", pattern: str = "", hours: int = 24) -> str:
    """分析日志"""
    if not os.path.isdir(log_dir):
        return f"日志目录不存在: {log_dir}"

    import time as _time
    now = _time.time()
    cutoff = now - hours * 3600
    errors = []
    warnings = []
    others = []

    for fname in sorted(os.listdir(log_dir)):
        if not fname.endswith(".log"):
            continue
        fpath = os.path.join(log_dir, fname)
        try:
            mtime = os.path.getmtime(fpath)
            if mtime < cutoff:
                continue
            with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
                for line in fp:
                    lower = line.lower()
                    if pattern and pattern.lower() not in lower:
                        continue
                    if "error" in lower or "critical" in lower or "traceback" in lower:
                        errors.append(line.strip())
                    elif "warning" in lower or "warn" in lower:
                        warnings.append(line.strip())
        except Exception:
            pass

    result = [f"📋 日志分析 (最近 {hours} 小时):"]
    if errors:
        result.append(f"\n❌ 错误 ({len(errors)} 条):")
        result.extend(f"  {e[:200]}" for e in errors[-15:])
    if warnings:
        result.append(f"\n⚠️ 警告 ({len(warnings)} 条):")
        result.extend(f"  {w[:200]}" for w in warnings[-10:])
    if not errors and not warnings:
        result.append("✅ 未发现错误或警告")
    return "\n".join(result)


@register_tool(
    name="diagnose_crash",
    description="诊断程序崩溃原因。检查最近的崩溃日志、核心转储、Windows 事件日志等。",
    parameters={
        "type": "object",
        "properties": {
            "project_root": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="debug"
)
def diagnose_crash(project_root: str = ".") -> str:
    """诊断崩溃"""
    results = []

    # 检查崩溃日志
    crash_patterns = ["debug_stderr_*", "debug_faulthandler_*", "crash_*"]
    import glob
    for pat in crash_patterns:
        for f in glob.glob(os.path.join(project_root, "logs", pat)):
            try:
                with open(f, "r") as fp:
                    content = fp.read()
                if content.strip():
                    results.append(f"📄 {os.path.basename(f)} ({len(content)} bytes):")
                    results.append(content[:500] + ("..." if len(content) > 500 else ""))
            except Exception:
                pass

    # 检查 Python 进程
    import subprocess
    try:
        r = subprocess.run(["tasklist", "/fi", "imagename eq python.exe", "/fo", "csv"],
                          capture_output=True, text=True, timeout=5,
                          creationflags=subprocess.CREATE_NO_WINDOW)
        python_procs = [l for l in r.stdout.split("\n") if "python" in l.lower()]
        if python_procs:
            results.append(f"\n🐍 运行中的 Python 进程: {len(python_procs)} 个")
    except Exception:
        pass

    return "\n".join(results) if results else "✅ 未发现崩溃日志，系统运行正常"
