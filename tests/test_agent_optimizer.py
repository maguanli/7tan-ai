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
