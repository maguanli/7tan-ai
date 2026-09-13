"""
console_panel._enqueue 去重逻辑单元测试

覆盖场景：
  1. 完全相同的日志行 → 去重
  2. 不同日志行 → 不去重
  3. 带 loguru 文件 sink 时间戳前缀的行 → 剥离前缀后与无前缀行去重（核心 bug 修复场景）
  4. 时间窗口过期后 → 不再去重（相同行可再次入队）
  5. ANSI 转义序列 → 剥离后参与去重
  6. 空行 / 纯空白行 → 直接丢弃
  7. 模糊指纹（前60字符相同）→ 去重
  8. 并发安全（多线程同时入队相同行）→ 仅入队一次

技术要点：
  - console_panel 顶部 import PyQt6 且模块级执行 install_all()，
    需在 import 前 stub PyQt6 模块树。
  - _dedup_map 是模块级全局，每个测试通过 fixture 清空。
"""

import sys
import time
import threading
import types
import queue as _queue_mod
from unittest.mock import MagicMock

import pytest

# ===== 1. Stub PyQt6（必须在 import console_panel 之前） =====
_pyqt6_modules = [
    "PyQt6",
    "PyQt6.QtWidgets",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
]

_saved_modules = {}


def _install_pyqt6_stub():
    """安装 PyQt6 stub，返回保存的原始模块引用"""
    for name in _pyqt6_modules:
        if name in sys.modules:
            _saved_modules[name] = sys.modules[name]
        mock_mod = MagicMock()
        # QtWidgets 需要这些类
        if name == "PyQt6.QtWidgets":
            mock_mod.QWidget = type("QWidget", (), {})
            mock_mod.QVBoxLayout = MagicMock
            mock_mod.QHBoxLayout = MagicMock
            mock_mod.QPushButton = MagicMock
            mock_mod.QLabel = MagicMock
            mock_mod.QTextEdit = MagicMock
            mock_mod.QScrollBar = MagicMock
        elif name == "PyQt6.QtCore":
            mock_mod.Qt = MagicMock()
            mock_mod.Qt.ScrollBarPolicy = MagicMock()
            mock_mod.QTimer = MagicMock
        elif name == "PyQt6.QtGui":
            mock_mod.QTextCursor = MagicMock
            mock_mod.QFont = MagicMock
        sys.modules[name] = mock_mod


def _remove_pyqt6_stub():
    """恢复原始模块"""
    for name in _pyqt6_modules:
        if name in _saved_modules:
            sys.modules[name] = _saved_modules[name]
        else:
            sys.modules.pop(name, None)
    _saved_modules.clear()


# ===== 2. Import console_panel（会执行 install_all） =====
_install_pyqt6_stub()
try:
    # 清除可能的 install_all 锁
    import src.ui.console_panel as cp
    cp.install_all._done = True  # 阻止 install_all 真正执行
    # 手动重置，因为 import 时已执行
    # 恢复 stdout/stderr（install_all 可能已重定向）
    if not isinstance(sys.stdout, type(sys.__stdout__)):
        sys.stdout = sys.__stdout__
    if not isinstance(sys.stderr, type(sys.__stderr__)):
        sys.stderr = sys.__stderr__
finally:
    _remove_pyqt6_stub()


# ===== 3. 测试 fixture =====

@pytest.fixture(autouse=True)
def _reset_dedup():
    """每个测试前清空去重映射和日志队列"""
    cp._dedup_map.clear()
    # 清空队列
    while True:
        try:
            cp._log_queue.get_nowait()
        except _queue_mod.Empty:
            break
    yield
    cp._dedup_map.clear()


def _drain_queue() -> list[str]:
    """取出队列中所有消息"""
    results = []
    while True:
        try:
            results.append(cp._log_queue.get_nowait())
        except _queue_mod.Empty:
            break
    return results


# ===== 4. 测试用例 =====


class TestDedupBasic:
    """基础去重功能"""

    def test_exact_duplicate_deduped(self):
        """完全相同的日志行应被去重"""
        cp._enqueue("hello world")
        cp._enqueue("hello world")
        results = _drain_queue()
        assert len(results) == 1
        assert "hello world" in results[0]

    def test_different_lines_not_deduped(self):
        """不同日志行不应被去重"""
        cp._enqueue("line A")
        cp._enqueue("line B")
        results = _drain_queue()
        assert len(results) == 2

    def test_empty_line_dropped(self):
        """空行应被丢弃"""
        cp._enqueue("")
        cp._enqueue("   ")
        cp._enqueue("\r\n")
        results = _drain_queue()
        assert len(results) == 0

    def test_line_gets_timestamp_prefix(self):
        """入队的行应带时间戳前缀"""
        cp._enqueue("test message")
        results = _drain_queue()
        assert len(results) == 1
        # 格式: HH:MM:SS │ message
        assert " │ " in results[0]
        assert "test message" in results[0]


class TestFileSinkPrefix:
    """loguru 文件 sink 时间戳前缀剥离（核心 bug 修复场景）"""

    def test_file_sink_prefix_stripped(self):
        """带文件 sink 前缀的行应被剥离前缀后与无前缀行去重"""
        cp._enqueue("💬 Agent: hello")
        cp._enqueue(
            "2026-07-22 20:52:13.123 | INFO     | "
            "src.agent.agent_loop:_run:227 | 💬 Agent: hello"
        )
        results = _drain_queue()
        assert len(results) == 1
        assert "💬 Agent: hello" in results[0]

    def test_file_sink_prefix_first(self):
        """文件 sink 行先入队，无前缀行后入队 → 也应去重"""
        cp._enqueue(
            "2026-07-22 20:52:13.456 | WARNING  | "
            "src.pipeline.task_queue:put:85 | task added"
        )
        cp._enqueue("task added")
        results = _drain_queue()
        assert len(results) == 1
        assert "task added" in results[0]

    def test_file_sink_regex_variants(self):
        """文件 sink 前缀的各种格式变体"""
        variants = [
            "2026-07-22 20:52:13.123 | INFO     | src.x:f:1 | msg",
            "2026-07-22 20:52:13.123 | DEBUG    | a.b.c:<lambda>:42 | msg",
            "2026-07-22 20:52:13.123 | CRITICAL | x:y:999 | msg",
        ]
        for v in variants:
            cp._enqueue("msg")
            cp._enqueue(v)
            results = _drain_queue()
            assert len(results) == 1, f"变体未去重: {v}"
            cp._dedup_map.clear()
            _drain_queue()


class TestTimeWindow:
    """时间窗口过期后不再去重"""

    def test_window_expired_allows_reenqueue(self):
        """超过精确去重窗口后，相同行应可再次入队"""
        cp._enqueue("repeatable")
        _drain_queue()
        # 手动将时间戳拨回窗口之前
        h = hash("repeatable")
        h_fuzzy = hash("repeatable"[:60])
        with cp._dedup_lock:
            cp._dedup_map[h] = time.time() - 10.0
            cp._dedup_map[h_fuzzy] = time.time() - 10.0
        cp._enqueue("repeatable")
        results = _drain_queue()
        assert len(results) == 1

    def test_within_window_still_deduped(self):
        """在时间窗口内，相同行仍应去重"""
        cp._enqueue("within window")
        cp._enqueue("within window")
        results = _drain_queue()
        assert len(results) == 1


class TestAnsiStrip:
    """ANSI 转义序列剥离"""

    def test_ansi_codes_stripped_before_dedup(self):
        """带 ANSI 颜色的行应与无颜色行去重"""
        cp._enqueue("\x1b[32mSUCCESS\x1b[0m task done")
        cp._enqueue("SUCCESS task done")
        results = _drain_queue()
        assert len(results) == 1
        assert "SUCCESS task done" in results[0]

    def test_pure_ansi_line_dropped(self):
        """纯 ANSI 转义序列（无可见内容）应被丢弃"""
        cp._enqueue("\x1b[32m\x1b[0m")
        results = _drain_queue()
        assert len(results) == 0


class TestFuzzyFingerprint:
    """模糊指纹去重（前60字符）"""

    def test_fuzzy_match_same_prefix(self):
        """前60字符相同但尾部不同的行应被模糊去重"""
        prefix = "x" * 60
        cp._enqueue(prefix + " tail A")
        cp._enqueue(prefix + " tail B")
        results = _drain_queue()
        # 前60字符相同 → 模糊指纹匹配 → 去重
        assert len(results) == 1

    def test_fuzzy_no_match_different_prefix(self):
        """前60字符不同的行不应被模糊去重"""
        cp._enqueue("A" + "x" * 59 + " tail")
        cp._enqueue("B" + "x" * 59 + " tail")
        results = _drain_queue()
        assert len(results) == 2


class TestConcurrency:
    """并发安全"""

    def test_concurrent_same_line_deduped(self):
        """多线程同时入队相同行，仅入队一次"""
        n_threads = 10
        barrier = threading.Barrier(n_threads)

        def worker():
            barrier.wait()
            cp._enqueue("concurrent line")

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        results = _drain_queue()
        assert len(results) == 1

    def test_concurrent_different_lines_all_enqueued(self):
        """多线程入队不同行，全部入队"""
        n = 20
        barrier = threading.Barrier(n)

        def worker(i):
            barrier.wait()
            cp._enqueue(f"unique line {i}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        results = _drain_queue()
        assert len(results) == n
