"""
agent_optimizer 单元测试

覆盖纯逻辑函数：模式识别、并行门槛、增量测试映射、工作区注入。
不依赖网络 / LLM / 重型库，可快速运行（增量测试场景友好）。
"""
import os
import sys
from pathlib import Path

import pytest

# 保证可以 import src 包（项目根目录加入 sys.path）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.agent_optimizer import (  # noqa: E402
    _should_parallel,
    _has_dependency,
    _extract_tool_name,
    _TOOL_DEPENDENCIES,
    _is_test_file,
    find_affected_tests,
    build_incremental_test_cmd,
    filter_history_by_mode,
    should_compress_context,
)


# ============================================================
# 并行门槛（建议A）
# ============================================================

def _mk_tc(name: str, call_id: str = "1") -> dict:
    return {"id": call_id, "function": {"name": name, "arguments": "{}"}}


class TestShouldParallel:
    def test_single_tool_no_parallel(self):
        assert _should_parallel([_mk_tc("grep_code")]) is False

    def test_all_readonly_fast_tools_no_parallel(self):
        calls = [_mk_tc("grep_code", "1"), _mk_tc("find_files", "2"),
                 _mk_tc("git_status", "3")]
        assert _should_parallel(calls) is False

    def test_cold_start_sensitive_no_parallel(self):
        calls = [_mk_tc("list_functions", "1"), _mk_tc("web_search", "2")]
        assert _should_parallel(calls) is False

    def test_slow_tool_enables_parallel(self):
        # run_command / write_file 不在只读集合 → 视为慢工具，允许并行
        calls = [_mk_tc("run_command", "1"), _mk_tc("write_file", "2")]
        assert _should_parallel(calls) is True


# ============================================================
# 测试文件识别 + 增量测试映射（建议D / 优化7）
# ============================================================

class TestIsTestFile:
    def test_prefix_test(self):
        assert _is_test_file("test_foo.py") is True

    def test_suffix_test(self):
        assert _is_test_file("foo_test.py") is True

    def test_normal_source(self):
        assert _is_test_file("foo.py") is False

    def test_conftest_not_matched_by_name(self):
        # conftest.py 不是测试文件名模式，但会触发同目录扫描
        assert _is_test_file("conftest.py") is False


class TestFindAffectedTests:
    def test_changed_test_file_returned_directly(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        tf = tests_dir / "test_bar.py"
        tf.write_text("def test_x(): pass", encoding="utf-8")
        result = find_affected_tests([str(tf)], project_root=str(tmp_path))
        assert str(tf) in result

    def test_source_file_maps_to_test(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        tf = tests_dir / "test_foo.py"
        tf.write_text("def test_x(): pass", encoding="utf-8")
        src_file = tmp_path / "src" / "foo.py"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("def foo(): pass", encoding="utf-8")
        result = find_affected_tests([str(src_file)], project_root=str(tmp_path))
        assert str(tf) in result

    def test_no_tests_dir_returns_empty(self, tmp_path):
        src_file = tmp_path / "foo.py"
        src_file.write_text("x = 1", encoding="utf-8")
        result = find_affected_tests([str(src_file)], project_root=str(tmp_path))
        assert result == []

    def test_empty_input(self):
        assert find_affected_tests([], project_root=".") == []


class TestBuildIncrementalCmd:
    def test_no_affected_returns_base(self, tmp_path):
        base = ["pytest", "tests/"]
        # tmp_path 下没有 tests 目录 -> 找不到受影响测试 -> 返回原命令
        src = tmp_path / "foo.py"
        src.write_text("x=1", encoding="utf-8")
        cmd = build_incremental_test_cmd(base, [str(src)], project_root=str(tmp_path))
        assert cmd == base

    def test_replaces_tests_path_with_affected(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        tf = tests_dir / "test_foo.py"
        tf.write_text("def test_x(): pass", encoding="utf-8")
        src = tmp_path / "foo.py"
        src.write_text("def foo(): pass", encoding="utf-8")
        base = ["pytest", "tests/"]
        cmd = build_incremental_test_cmd(base, [str(src)], project_root=str(tmp_path))
        assert "pytest" in cmd
        assert str(tf) in cmd
        assert "tests/" not in cmd  # 已被具体测试文件替换


# ============================================================
# 历史过滤 / 上下文压缩判断
# ============================================================

class TestFilterHistory:
    def test_short_history_kept(self):
        hist = [{"role": "user", "content": "你好"}]
        out = filter_history_by_mode(hist, "code")
        assert len(out) >= 1

    def test_empty_history(self):
        assert filter_history_by_mode([], "code") == []


class TestShouldCompress:
    def test_below_threshold(self):
        assert should_compress_context(5000, threshold=20000) is False

    def test_above_threshold(self):
        assert should_compress_context(25000, threshold=20000) is True

    def test_at_boundary(self):
        # 边界值：恰好等于阈值
        result = should_compress_context(20000, threshold=20000)
        assert isinstance(result, bool)


# ============================================================
# ⭐ _has_dependency 边界情况（钉死依赖判断逻辑）
# ============================================================

class TestHasDependency:
    """同批依赖 / 传递依赖 / 无依赖 / 自引用等边界。"""

    def test_no_dependency_table_entry_returns_false(self):
        # 不在依赖表中的工具 → 永远无依赖（宽松方向）
        calls = [_mk_tc("grep_code", "1"), _mk_tc("write_file", "2")]
        assert _has_dependency(calls[0], calls) is False

    def test_same_batch_dependency_detected(self):
        # 同批：run_tests 依赖 write_file
        calls = [_mk_tc("write_file", "1"), _mk_tc("run_tests", "2")]
        assert _has_dependency(calls[1], calls) is True
        # 反向：write_file 不依赖 run_tests
        assert _has_dependency(calls[0], calls) is False

    def test_dependency_absent_in_batch(self):
        # run_tests 在依赖表中，但批内没有它的前置 → 无依赖
        calls = [_mk_tc("run_tests", "1"), _mk_tc("grep_code", "2")]
        assert _has_dependency(calls[0], calls) is False

    def test_transitive_chain_each_hop_flagged(self):
        # 传递链：write_file → git_add → git_commit → git_push
        # 依赖判断是逐跳的（非递归），每一跳都应被标记
        calls = [
            _mk_tc("write_file", "1"),
            _mk_tc("git_add", "2"),
            _mk_tc("git_commit", "3"),
            _mk_tc("git_push", "4"),
        ]
        # git_add 依赖 write_file
        assert _has_dependency(calls[1], calls) is True
        # git_commit 依赖 git_add（同批存在）
        assert _has_dependency(calls[2], calls) is True
        # git_push 依赖 git_commit（同批存在）
        assert _has_dependency(calls[3], calls) is True
        # write_file 无依赖
        assert _has_dependency(calls[0], calls) is False

    def test_transitive_not_recursive(self):
        # git_push 的直接依赖是 git_commit；批内只有 write_file 时
        # git_push 不递归检测到 write_file → False（验证非递归语义）
        calls = [_mk_tc("write_file", "1"), _mk_tc("git_push", "2")]
        assert _has_dependency(calls[1], calls) is False

    def test_self_not_counted_as_dependency(self):
        # 单个工具，批内只有自己 → 不应自我依赖
        calls = [_mk_tc("run_tests", "1")]
        assert _has_dependency(calls[0], calls) is False

    def test_empty_name_returns_false(self):
        # 工具名为空 → 安全返回 False
        tc = {"id": "1", "function": {"name": "", "arguments": "{}"}}
        assert _has_dependency(tc, [tc]) is False

    def test_extract_tool_name_variants(self):
        # _extract_tool_name 对各种结构健壮
        assert _extract_tool_name(_mk_tc("grep_code")) == "grep_code"
        assert _extract_tool_name({"function": {}}) == ""
        assert _extract_tool_name({}) == ""
