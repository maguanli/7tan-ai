"""
性能分析工具 — 代码计时、内存分析、热点识别
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import os
import time as _time


@register_tool(
    name="benchmark_function",
    description="对 Python 函数进行基准测试：运行N次，统计最小/最大/平均/中位数执行时间。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Python 文件路径"},
            "function_name": {"type": "string", "description": "要测试的函数名"},
            "args": {"type": "string", "description": "函数参数（Python 表达式），如 '100, \"hello\"'", "default": ""},
            "runs": {"type": "integer", "description": "运行次数", "default": 10},
        },
        "required": ["file_path", "function_name"]
    },
    category="perf"
)
def benchmark_function(file_path: str, function_name: str,
                       args: str = "", runs: int = 10) -> str:
    """基准测试"""
    if not os.path.isfile(file_path):
        return f"文件不存在: {file_path}"

    import statistics
    try:
        # 动态加载模块
        import importlib.util
        spec = importlib.util.spec_from_file_location("_bench_target", file_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        func = getattr(mod, function_name)
    except Exception as e:
        return f"加载函数失败: {e}"

    # 解析参数
    parsed_args = []
    try:
        if args:
            parsed_args = eval(f"[{args}]")
    except Exception as e:
        return f"参数解析失败: {e}"

    # 预热
    try:
        func(*parsed_args)
    except Exception as e:
        return f"函数调用失败: {e}"

    # 正式测试
    times = []
    errors = 0
    for _ in range(runs):
        try:
            start = _time.perf_counter()
            func(*parsed_args)
            elapsed = (_time.perf_counter() - start) * 1000
            times.append(elapsed)
        except Exception:
            errors += 1

    if not times:
        return "所有运行均失败"

    results = [f"⏱ 基准测试: {function_name}() × {runs} 次\n"]
    results.append(f"  最小: {min(times):.2f}ms")
    results.append(f"  最大: {max(times):.2f}ms")
    results.append(f"  平均: {statistics.mean(times):.2f}ms")
    results.append(f"  中位数: {statistics.median(times):.2f}ms")
    if len(times) > 1:
        results.append(f"  标准差: {statistics.stdev(times):.2f}ms")
    if errors:
        results.append(f"  失败: {errors} 次")
    return "\n".join(results)


@register_tool(
    name="profile_code_block",
    description="使用 cProfile 分析 Python 代码的性能热点：找出耗时最多的函数调用。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Python 文件路径"},
            "function_name": {"type": "string", "description": "入口函数名", "default": ""},
        },
        "required": ["file_path"]
    },
    category="perf"
)
def profile_code_block(file_path: str, function_name: str = "") -> str:
    """性能分析"""
    import cProfile, pstats, io

    if not function_name:
        return "请指定要分析的函数名"

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_prof_target", file_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        func = getattr(mod, function_name)
    except Exception as e:
        return f"加载失败: {e}"

    prof = cProfile.Profile()
    prof.enable()
    try:
        func()
    except Exception as e:
        try:
            func()
        except Exception as e2:
            prof.disable()
            return f"函数调用失败: {e2}"
    prof.disable()

    s = io.StringIO()
    ps = pstats.Stats(prof, stream=s).sort_stats("cumulative")
    ps.print_stats(20)

    return (f"🔍 性能分析: {function_name}()\n"
            f"   Profiler: cProfile (按累计耗时排序，前20)\n\n"
            f"{s.getvalue()}")


@register_tool(
    name="check_memory",
    description="检查 Python 进程的内存使用情况和项目磁盘占用。",
    parameters={
        "type": "object",
        "properties": {
            "project_root": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="perf"
)
def check_memory(project_root: str = ".") -> str:
    """内存/磁盘检查"""
    results = []

    # Python 进程内存
    try:
        import psutil
        proc = psutil.Process()
        mem = proc.memory_info()
        results.append(f"🐍 当前进程:")
        results.append(f"   RSS: {mem.rss/1024/1024:.1f} MB")
        results.append(f"   VMS: {mem.vms/1024/1024:.1f} MB")
        results.append(f"   CPU: {proc.cpu_percent(interval=0.1):.1f}%")
    except ImportError:
        results.append("💡 安装 psutil 获取进程内存: pip install psutil")
    except Exception:
        pass

    # 磁盘占用
    import subprocess
    try:
        r = subprocess.run(["powershell", "-Command",
            f"Get-ChildItem -Path '{os.path.abspath(project_root)}' -Recurse -File | Measure-Object -Property Length -Sum | Select-Object -ExpandProperty Sum"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW)
        total_bytes = int(r.stdout.strip() or 0)
        results.append(f"\n📁 项目总大小: {total_bytes/1024/1024:.1f} MB")
    except Exception:
        pass

    # 大目录分析
    results.append("\n📊 目录大小:")
    total = 0
    for entry in sorted(os.scandir(project_root), key=lambda e: -_dir_size(e)):
        if total >= 10:
            break
        size = _dir_size(entry)
        if size > 1024:  # > 1KB
            results.append(f"  {size/1024/1024:8.1f} MB  {entry.name}")
            total += 1

    return "\n".join(results)


def _dir_size(entry) -> int:
    try:
        if entry.is_file():
            return entry.stat().st_size
        total = 0
        for sub in os.scandir(entry.path):
            if sub.name.startswith(".") or sub.name == "node_modules":
                continue
            total += _dir_size(sub)
        return total
    except Exception:
        return 0
