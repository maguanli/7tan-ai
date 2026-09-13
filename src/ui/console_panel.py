
"""
实时控制台面板 — 嵌入工作台左侧，替代命令行黑窗

多层捕获策略：
  1. loguru sink — 直接注册到 loguru，捕获所有 logger 输出
  2. Python 重定向 — 替换 sys.stdout / sys.stderr
  3. OS 管道 — os.dup2()（有 console 时生效）

修复记录 (2025-07-18):
  - P1-3: _log_queue 改为无界队列，避免队列满导致管道阻塞 → GUI 假死
  - P1-4: _install_os_pipe 去掉 os.write(saved_out) 回写，避免死循环
  - P2-5: install_all() 加文件锁防重入
  - P3-6: QPlainTextEdit → QTextEdit + insertHtml 语法高亮，不再逐行 appendPlainText
  - P4-7: _enqueue 加去重哈希环(最近200条)，消除三层捕获导致的2~3倍重复日志
  - P5-8: 简化高亮规则，去掉过度花哨的 CSS 边框/背景
  - P6-9: _enqueue 去重逻辑加 threading.Lock()，修复并发竞态导致重复仍出现；扩大哈希环到500
  - P7-10: 修复中文边界不可靠（w是否含CJK取决于平台），改用lookbehind边界；增加Agent/User角色专属颜色；修复OK语法错误
  - P8-11: 去重从计数哈希环改为时间窗口(3秒)，彻底解决日志量大时哈希环被挤出导致重复的问题
  - P9-12: 增加模糊指纹(前60字符hash)，防止loguru默认sink带时间戳的格式化绕过精确去重
"""
import os
import sys
import re
import html as _html_lib
import queue
import threading
import tempfile
from datetime import datetime
import time as _time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QScrollBar,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTextCursor, QFont

import logging
from loguru import logger

# ===== ANSI =====
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


# ===== 语法高亮规则 =====
_HIGHLIGHT_RULES: list[tuple[str, str]] = [
    (r'💬\s*Agent:', '#00d4ff'),
    (r'👤\s*User:', '#fbbf24'),
    (r'\b(ERROR|CRITICAL|FATAL|Traceback|❌|💥|🔴)\b', '#ef4444'),
    (r'\b(WARNING|WARN|⚠️|⚠|🟠)\b', '#f59e0b'),
    (r'\bSUCCESS\b', '#10b981'),
    (r'\bOK\b', '#10b981'),
    (r'\b(INFO|ℹ️|🔵)\b', '#3b82f6'),
    (r'\b(DEBUG|🐛)\b', '#8b5cf6'),
    (r'(?<!\w)(正在|开始|启动|🚀|⏳|🔄|📦|🔧)(?!\w)', '#00d4ff'),
    (r'(?<!\w)(完成|成功|就绪|通过|正常|✅|🟢|🎉)(?!\w)', '#10b981'),
    (r'(?<!\w)(失败|错误|异常|超时|崩溃|拒绝|不可用)(?!\w)', '#ef4444'),
    (r'\bhttps?://\S+', '#60a5fa'),
    (r'\b[A-Za-z_]+\.py\b', '#fbbf24'),
    (r'(?<!\w)(\d+\.?\d*)\s*(GB|MB|KB|秒|s|ms|行|条)(?!\w)', '#fb923c'),
    (r'\b(True|False|None)\b', '#c084fc'),
]

_HIGHLIGHT_PATTERNS = [(re.compile(p), c) for p, c in _HIGHLIGHT_RULES]


# 快速预筛：合并 16 条规则为一条 alternation 正则，单次 search 判断是否命中
# （普通行一次失败即返回，命中行也只需一次全量 sub，省 16 次独立正则扫描）
_COMBINED_RULES = "|".join(f"(?:{p})" for p, _ in _HIGHLIGHT_RULES)
_HIGHLIGHT_PROBE = re.compile(_COMBINED_RULES)

# 颜色映射：probe 命中后仍需逐规则上色（命中行是少数，成本可接受）
def _highlight_line(text: str) -> str:
    escaped = _html_lib.escape(text, quote=False)
    # 预筛：单条组合正则，一次扫描，90%+ 普通行在此快速返回
    if not _HIGHLIGHT_PROBE.search(text[:2000]):
        return escaped
    result = escaped
    for pattern, color in _HIGHLIGHT_PATTERNS:
        result = pattern.sub(
            lambda m, c=color: f'<span style="color:{c};font-weight:bold;">{m.group(0)}</span>',
            result,
        )
    return result


# ===== 全局日志队列 =====
_log_queue = queue.Queue()
# 时间窗口去重 + 模糊指纹：双重防重复
_dedup_map: dict = {}  # {hash: timestamp}
_dedup_lock = threading.Lock()
_DEDUP_WINDOW = 3.0
_DEDUP_FUZZY_WINDOW = 2.0
_dedup_cleanup_counter = 0


_FILE_SINK_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s*\|\s*"
    r"[A-Z]+\s*\|\s*[\w\.]+:[\w<>]+:\d+\s*\|\s*")


def _enqueue(line: str):
    line = line.strip('\r\n')
    if not line:
        return
    clean = _strip_ansi(line)
    if not clean.strip():
        return
    clean = _FILE_SINK_RE.sub('', clean)
    if not clean.strip():
        return
    # 过滤启动噪音和底层 HTTP 库的啰嗦日志，保持控制台清爽
    _NOISE_PATTERNS = [
        '🔧 注册工具',
        '📦 插件已加载',
        '✅ 数据库初始化完成',
        '[系统] loguru 控制台 sink 已连接',
        '[系统] 标准 logging 桥接已安装',
        '[系统] Python stdout/stderr 重定向已安装',
        '[系统] OS 管道已安装',
        '[系统] GUI 模式，跳过 OS 管道',
        '[系统] loguru sink 失败',
        'Sending HTTP Request',
    ]
    for np_ in _NOISE_PATTERNS:
        if np_ in clean:
            return
    h = hash(clean)
    # 模糊指纹：取前60字符，防止loguru默认sink格式化(带时间戳)绕过精确去重
    h_fuzzy = hash(clean[:60])
    now = _time.time()
    with _dedup_lock:
        global _dedup_cleanup_counter
        # 计数触发清理，不在每条日志热路径上遍历字典
        _dedup_cleanup_counter += 1
        if _dedup_cleanup_counter > 500:
            _dedup_cleanup_counter = 0
            cutoff = now - max(_DEDUP_WINDOW, _DEDUP_FUZZY_WINDOW) * 2
            if len(_dedup_map) > 5000:
                _dedup_map.clear()
            else:
                stale = [k for k, v in _dedup_map.items() if v < cutoff]
                for k in stale:
                    del _dedup_map[k]
        # 精确匹配
        last_ts = _dedup_map.get(h)
        if last_ts is not None and (now - last_ts) < _DEDUP_WINDOW:
            return
        # 模糊匹配（防止不同格式化绕过）
        last_ts_fuzzy = _dedup_map.get(h_fuzzy)
        if last_ts_fuzzy is not None and (now - last_ts_fuzzy) < _DEDUP_FUZZY_WINDOW:
            return
        _dedup_map[h] = now
        _dedup_map[h_fuzzy] = now
    ts = datetime.now().strftime("%H:%M:%S")
    _log_queue.put(f"{ts} │ {clean}")
    # NOTE: 朗读检测不在 _enqueue 里做！
    # 此处位于 loguru sink emit 链中，若同步调用 _maybe_speak_agent_line
    # → 内部 logger.info → loguru 重入 → error interceptor → sys.stderr
    # → _StreamRedirector.write → 与当前 sink 争同一把锁 → 死锁（历史 3 次未响应根因）
    # 朗读检测已移到 _drain_queue（QTimer 事件循环，不在 emit 链中）。


# ===== 控制台 Agent 内容朗读（实时控制台显示 Agent 回复时同步发声） =====
_AGENT_LINE_RE = re.compile(r'💬\s*Agent:\s*(.+)$', re.S)
_console_tts_registered = False

# —— Agent 截断行(中间迭代)朗读：最新优先 + 2 秒合并窗口（防刷屏堆积） ——
_trunc_pending_text = None      # 待朗读的最新截断内容
_trunc_pending_timer = None     # 合并窗口定时器
_trunc_lock = threading.Lock()

# —— 忙碌暂存（最新一条），播放完成后自动补读（修复"忙碌即丢弃"导致的漏读） ——
_pending_speak = None          # (text, trunc_prefix) 或 None
_pending_speak_lock = threading.Lock()

# —— 最后实际朗读的截断前缀（最终回复跳过此前缀，防"重读前面一小部分"） ——
_last_trunc_read = None
_last_trunc_read_lock = threading.Lock()


def _set_pending_speak(text, trunc_prefix=None):
    """暂存待补读内容（最新覆盖旧，只保留一条；trunc_prefix 为截断前缀）"""
    global _pending_speak
    with _pending_speak_lock:
        _pending_speak = (text, trunc_prefix)


def _take_pending_speak():
    """取走待补读内容（取走后清空，返回 (text, trunc_prefix) 或 None）"""
    global _pending_speak
    with _pending_speak_lock:
        t = _pending_speak
        _pending_speak = None
    return t


def _clear_pending_speak():
    """清空待补读内容（最终回复优先时丢弃暂存中间内容）"""
    global _pending_speak
    with _pending_speak_lock:
        _pending_speak = None


def reset_console_speech_state():
    """清空控制台朗读的待读缓冲（用户发新消息 / 打断上一次朗读时调用）。

    只清“待读”状态，不动全局去重登记（避免同一内容被反复朗读）：
      - 取消截断合并窗口定时器，丢弃待读的截断内容
      - 丢弃忙碌暂存内容（否则打断后“播放完成回调”会把旧内容又补读一遍）
      - 清空“已读截断前缀”（新回复重新计算，防误跳过新内容）

    必须先于 tts_stop() 调用，否则 tts_stop 触发的播放完成回调会补读旧内容。
    """
    global _trunc_pending_text, _trunc_pending_timer, _last_trunc_read
    with _trunc_lock:
        if _trunc_pending_timer is not None:
            try:
                _trunc_pending_timer.cancel()
            except Exception:
                pass
            _trunc_pending_timer = None
        _trunc_pending_text = None
    _clear_pending_speak()
    with _last_trunc_read_lock:
        _last_trunc_read = None


def _speak_console_async(text: str, trunc_prefix: str = None):
    """后台朗读控制台 Agent 内容（带防重复 + 播放中检测 + 全链路日志）。

    防重复策略（与聊天页/全局桥协调，原子抢占保证只出声一次）：
      1. tts_is_spoken(text) — 已有通道登记（含本通道抢占/聊天页已读）→ 跳过
      2. tts_is_busy()       — 正在播放 → 暂存待补读（不漏读，播完自动补读）
      3. tts_speak_dedup()   — 全局去重合成播放（5 分钟同一全文只读一次）
      4. 实际朗读成功且 trunc_prefix 非空 → 记录截断前缀（供最终回复跳过，防重读前面部分）

    Args:
        text: 要朗读的文本
        trunc_prefix: 截断行前缀（不含尾部省略号）；朗读成功时记录，最终回复据此跳过已读前缀
    """
    if not text or not text.strip():
        return

    def _do():
        global _last_trunc_read
        try:
            from src.agent.speak_bridge import _voice_mode_enabled
            if not _voice_mode_enabled():
                logger.info("[TTS-Console] 语音模式关闭，跳过朗读")
                return
            from data.plugins.tts_piper.tools import tts_speak_dedup, tts_is_busy, tts_is_spoken
            # 已在去重窗口内朗读过 → 跳过（不暂存，防重复）
            if tts_is_spoken(text):
                logger.info("[TTS-Console] 该内容已朗读过（去重窗口内），跳过")
                return
            if tts_is_busy():
                # 🔧 修复漏读：忙碌不再丢弃，暂存最新一条，播放完成后自动补读
                _set_pending_speak(text, trunc_prefix)
                logger.info("[TTS-Console] 正在播放中，暂存待补读（最新一条）")
                return
            # 🔊 控制台可见反馈（是否真正出声由全局去重裁决：与聊天页共用同一套去重，只读一遍）
            logger.info("[TTS-Console] 🔊 开始朗读 Agent 回复（{}字）", len(text))
            r = tts_speak_dedup(text)
            if r.get("skipped"):
                msg = r.get("message", "?")
                # 合成互斥/合成中 → 暂存待补读（不漏）；纯去重（已朗读）→ 丢弃
                if "互斥" in msg or "合成" in msg:
                    _set_pending_speak(text, trunc_prefix)
                    logger.info("[TTS-Console] 合成互斥，暂存待补读（{}）", msg)
                else:
                    logger.info("[TTS-Console] 朗读被全局去重拦截（{}），跳过（防重复）", msg)
                return
            if r.get("status") == "ok":
                # ✅ 实际朗读成功 → 记录截断前缀（供最终回复跳过，防重读前面部分）
                if trunc_prefix:
                    with _last_trunc_read_lock:
                        _last_trunc_read = trunc_prefix
                logger.info(
                    "[TTS-Console] 控制台朗读完成: engine={} size={}KB",
                    r.get("engine", "?"), r.get("size_kb", "?"),
                )
            else:
                logger.warning("[TTS-Console] 控制台朗读失败: {}", r.get("message", "?"))
        except Exception as e:
            logger.warning("[TTS-Console] 朗读异常: {}: {}", type(e).__name__, e)

    threading.Thread(target=_do, daemon=True).start()


def _speak_final_reply(content: str) -> None:
    """朗读最终完整回复：跳过已朗读的截断前缀（防"重读前面一小部分"）。

    1. 若内容以最后实际朗读的截断前缀开头 → 只读新增部分（前缀已读过），
       并先登记全文已读，防其他通道（聊天页/全局桥）再次全文朗读 → 重读前缀；
       若内容与截断前缀完全相同 → 全部已读过，跳过朗读。
    2. 无前缀可跳 → 正常全文朗读（由 tts_speak_dedup 内部登记去重）。
    """
    global _last_trunc_read
    if not content or not content.strip():
        return
    read_text = content
    with _last_trunc_read_lock:
        prefix = _last_trunc_read
        _last_trunc_read = None
    if prefix:
        if content == prefix:
            logger.info("[TTS-Console] 最终回复与已读截断内容相同，跳过朗读（防重读）")
            return
        if content.startswith(prefix):
            read_text = content[len(prefix):]
            logger.info(
                "[TTS-Console] 最终回复跳过已读前缀（{}字），只读新增部分（{}字）",
                len(prefix), len(read_text),
            )
            # 登记全文已读：防聊天页/全局桥等其他通道再次全文朗读 → 重读前缀
            try:
                from data.plugins.tts_piper.tools import tts_mark_spoken
                tts_mark_spoken(content)
            except Exception as e:
                logger.warning("[TTS-Console] 全文去重登记失败: {}", e)
    _speak_console_async(read_text)


def _console_tts_callback(text: str):
    """agent_loop 最终回复回调：控制台朗读（跳过已读截断前缀，防重读前面部分）"""
    if text and text.strip():
        _speak_final_reply(text)


def _on_console_play_finished():
    """播放完成回调：若播放队列空闲且有暂存内容 → 自动补读（修复"忙碌即丢弃"漏读）"""
    try:
        from data.plugins.tts_piper.tools import tts_is_busy
        if tts_is_busy():
            # 队列已有新内容在播 → 保持暂存，等下一次完成回调再补读
            return
        item = _take_pending_speak()
        if item:
            text, trunc_prefix = item
            logger.info("[TTS-Console] ▶ 播放完成，补读暂存内容（{}字）", len(text))
            _speak_console_async(text, trunc_prefix)
    except Exception as e:
        logger.warning("[TTS-Console] 补读回调异常: {}: {}", type(e).__name__, e)


def init_console_tts():
    """注册控制台朗读回调（幂等，多播不覆盖聊天页/全局桥）"""
    global _console_tts_registered
    if _console_tts_registered:
        return
    _console_tts_registered = True
    try:
        from src.agent.agent_loop import register_agent_speak_callback, _agent_speak_callbacks
        register_agent_speak_callback(_console_tts_callback)
        # 🔧 播放完成回调：空闲时补读忙碌暂存的内容（修复漏读）
        from data.plugins.tts_piper.tools import register_tts_finish_callback
        register_tts_finish_callback(_on_console_play_finished)
        logger.info(
            "[TTS-Console] 控制台朗读已注册（agent 最终回复回调，当前回调数={}）",
            len(_agent_speak_callbacks),
        )
    except Exception as e:
        logger.warning("[TTS-Console] 注册失败: {}: {}", type(e).__name__, e)


def _flush_trunc_pending():
    """合并窗口到期：朗读暂存的最新截断内容（最新优先，只读一条）"""
    global _trunc_pending_text, _trunc_pending_timer
    with _trunc_lock:
        text = _trunc_pending_text
        _trunc_pending_text = None
        _trunc_pending_timer = None
    if text:
        # 🔧 去掉尾部省略号再朗读（避免读成"点点点"），并记录截断前缀供最终回复跳过
        prefix = text[:-3].rstrip() if text.endswith("...") else None
        clean_text = prefix if prefix else text
        if clean_text:
            logger.info("[TTS-Console] 🔊 朗读 Agent 实时内容（{}字）", len(clean_text))
            _speak_console_async(clean_text, trunc_prefix=prefix)


def _cancel_trunc_pending():
    """最终完整回复到达：取消待读的截断内容（只读最终回复）"""
    global _trunc_pending_text, _trunc_pending_timer
    with _trunc_lock:
        if _trunc_pending_timer is not None:
            try:
                _trunc_pending_timer.cancel()
            except Exception:
                pass
            _trunc_pending_timer = None
        _trunc_pending_text = None
    # 🔧 最终回复优先：丢弃暂存的中间内容，只读最终回复
    _clear_pending_speak()


def _maybe_speak_agent_line(line: str):
    """检测 💬 Agent 日志行 → 后台朗读（agent 回调的补充通道）。

    规则（用户要求：💬 Agent 内容全部朗读）：
      - 中间迭代截断输出（`content[:100]...`）→ 朗读：2 秒合并窗口内多条只读最新一条（实时播报，不堆积）
      - 最终完整回复（无省略号）→ 立即朗读，并取消待读的截断内容
      - 防重复/防叠加由 _speak_console_async 统一处理
    """
    global _trunc_pending_text, _trunc_pending_timer
    m = _AGENT_LINE_RE.search(line)
    if not m:
        return
    content = m.group(1).strip()
    if not content:
        return
    is_truncated = content.endswith("...")
    if is_truncated:
        # 截断内容：暂存最新一条，2 秒合并窗口结束后朗读（实时播报，不堆积）
        with _trunc_lock:
            _trunc_pending_text = content
            if _trunc_pending_timer is None:
                _trunc_pending_timer = threading.Timer(2.0, _flush_trunc_pending)
                _trunc_pending_timer.daemon = True
                _trunc_pending_timer.start()
        logger.debug("[TTS-Console] Agent 实时内容已收录（{}字，稍后朗读）", len(content))
        return
    # 最终完整回复：优先朗读（取消待读截断行 + 跳过已读截断前缀防重读）
    _cancel_trunc_pending()
    logger.info("[TTS-Console] 检测到 Agent 完整回复，触发朗读（{}字）", len(content))
    _speak_final_reply(content)


# ===== 1. Standard logging bridge =====
class _LoggingBridge(logging.Handler):
    """桥接标准 logging → 控制台队列"""
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        try:
            msg = self.format(record)
            _enqueue(msg)
        except Exception:
            self.handleError(record)


_logging_bridge_installed = False


def _add_std_logging_bridge():
    """安装标准 logging 桥接，让 logging.getLogger 的日志也显示在控制台"""
    global _logging_bridge_installed
    if _logging_bridge_installed:
        return
    _logging_bridge_installed = True
    root_logger = logging.getLogger()
    root_logger.addHandler(_LoggingBridge())
    root_logger.setLevel(logging.DEBUG)
    _enqueue("[系统] 标准 logging 桥接已安装")


# ===== 2. loguru sink =====
_loguru_sink_id = None


def _add_loguru_sink():
    global _loguru_sink_id
    try:
        from loguru import logger
        if _loguru_sink_id is not None:
            try:
                logger.remove(_loguru_sink_id)
            except Exception:
                pass
        try:
            logger.remove(0)
        except Exception:
            pass
        _loguru_sink_id = logger.add(
            lambda msg: _enqueue(str(msg).strip()),
            format="{message}",
            level="DEBUG",
            colorize=False,
        )
        _enqueue("[系统] loguru 控制台 sink 已连接")
    except ImportError:
        pass
    except Exception as e:
        _enqueue(f"[系统] loguru sink 失败: {e}")


# ===== 2. Python stdout/stderr 重定向 =====
class _StreamRedirector:
    def __init__(self):
        self._buf = ""
        # 🔒 RLock：loguru error interceptor 重入写 stderr 时（同线程）
        # 普通 Lock 会死等自己持有的锁 → 应用假死；RLock 允许同线程重入
        self._lock = threading.RLock()

    def write(self, s):
        if not s:
            return
        with self._lock:
            self._buf += s
            while '\n' in self._buf:
                line, self._buf = self._buf.split('\n', 1)
                _enqueue(line)

    def flush(self):
        with self._lock:
            if self._buf:
                _enqueue(self._buf)
                self._buf = ""

    def isatty(self):
        return False

    def fileno(self):
        try:
            return sys.__stderr__.fileno()
        except Exception:
            raise OSError("no fileno")


_redirector = None


def _install_python_redirect():
    global _redirector
    _redirector = _StreamRedirector()
    sys.stdout = _redirector
    sys.stderr = _redirector
    _enqueue("[系统] Python stdout/stderr 重定向已安装")


# ===== 3. OS 管道 =====
def _install_os_pipe():
    try:
        os.dup(1)
    except OSError:
        _enqueue("[系统] GUI 模式，跳过 OS 管道")
        return

    r, w = os.pipe()
    os.dup2(w, 1)
    os.dup2(w, 2)

    def _reader():
        buf = b""
        while True:
            try:
                chunk = os.read(r, 8192)
                if not chunk:
                    break
                buf += chunk
                while b'\n' in buf:
                    lb, buf = buf.split(b'\n', 1)
                    _enqueue(lb.decode('utf-8', errors='replace').rstrip('\r'))
            except Exception:
                break

    threading.Thread(target=_reader, daemon=True, name="pipe").start()
    _enqueue("[系统] OS 管道已安装")


_install_lock_path = os.path.join(tempfile.gettempdir(),
                                  f"7tan_console_install_{os.getpid()}.lock")


def install_all():
    if getattr(install_all, '_done', False):
        return
    if os.path.exists(_install_lock_path):
        return
    install_all._done = True
    try:
        with open(_install_lock_path, 'w') as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
    _install_python_redirect()
    _install_os_pipe()
    _add_std_logging_bridge()
    _add_loguru_sink()
    try:
        init_console_tts()
    except Exception:
        pass
    import atexit
    @atexit.register
    def _cleanup_lock():
        try:
            os.remove(_install_lock_path)
        except Exception:
            pass


install_all()


def refresh_loguru_sink():
    _add_loguru_sink()


# ===== UI：实时控制台 =====
CONSOLE_THEME = {
    "accent": "#00d4ff",
    "accent2": "#7c3aed",
    "danger": "#ef4444",
    "text_primary": "#e2e8f0",
    "text_secondary": "#94a3b8",
    "border": "#1e293b",
    "bg_dark": "#1a1a2e",
    "bg_input": "#1e1e3a",
}


class ConsoleViewer(QWidget):
    """实时日志控制台 — QTextEdit + insertHtml 高亮"""

    def __init__(self):
        super().__init__()
        T = CONSOLE_THEME

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ── 顶部工具栏 ──
        bar = QHBoxLayout()
        title = QLabel("📟 实时控制台")
        title.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {T['text_primary']};")
        bar.addWidget(title)

        # ── 代码修改实时按钮（打开实时变更面板，AI 修改代码时自动弹出）──
        self._diff_btn = QPushButton("🔧 代码修改实时")
        self._diff_btn.setFixedHeight(26)
        self._diff_btn.setToolTip("打开代码修改实时面板，实时查看 AI 修改代码的 diff")
        self._diff_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T['accent2']}33; color: {T['accent2']};
                border: 1px solid {T['accent2']}66; border-radius: 4px;
                padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {T['accent2']}55; }}
        """)
        self._diff_btn.clicked.connect(self._open_diff_panel)
        bar.addWidget(self._diff_btn)

        bar.addStretch()

        self._diff_panel = None
        self._auto_scroll = True
        self._auto_btn = QPushButton("🔽 自动滚动")
        self._auto_btn.setCheckable(True)
        self._auto_btn.setChecked(True)
        self._auto_btn.setFixedHeight(26)
        self._auto_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T['accent']}33; color: {T['accent']};
                border: 1px solid {T['accent']}66; border-radius: 4px;
                padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:checked {{ background: {T['accent']}66; }}
            QPushButton:hover {{ background: {T['accent']}44; }}
        """)
        self._auto_btn.clicked.connect(
            lambda: setattr(self, '_auto_scroll', self._auto_btn.isChecked()))
        bar.addWidget(self._auto_btn)

        clear_btn = QPushButton("🗑 清空")
        clear_btn.setFixedHeight(26)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T['danger']}22; color: {T['danger']};
                border: 1px solid {T['danger']}44; border-radius: 4px;
                padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {T['danger']}44; }}
        """)
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        # 🔒 行数硬上限：文档无限增长会导致 setValue(maximum()) 全量重排 → 主线程假死
        self._output.document().setMaximumBlockCount(2000)
        clear_btn.clicked.connect(self._output.clear)
        bar.addWidget(clear_btn)

        self._line_count = QLabel("0 行")
        self._line_count.setStyleSheet(
            f"color: {T['text_secondary']}; font-size: 11px; padding: 2px 6px;")
        bar.addWidget(self._line_count)
        layout.addLayout(bar)

        # ── 输出区 ──
        self._output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._output.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._output.setStyleSheet(f"""
            QTextEdit {{
                background-color: #0D1117;
                color: #C9D1D9;
                border: 1px solid {T['border']};
                border-radius: 6px;
                font-family: "Cascadia Code", "Fira Code", "Consolas",
                             "Courier New", monospace;
                font-size: 12px;
                padding: 8px;
                selection-background-color: #264F78;
            }}
        """)
        layout.addWidget(self._output, 1)

        # ── 底部状态 ──
        status = QLabel(
            "loguru + Python + OS 管道  |  语法高亮  |  时间窗口去重(3s)")
        status.setStyleSheet(
            f"color: {T['text_secondary']}; font-size: 11px; "
            f"padding: 2px 4px;")
        layout.addWidget(status)

        self._total_lines = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._drain_queue)
        self._timer.start(50)

    def attach_diff_panel(self, panel):
        """绑定代码修改实时面板（由主窗口创建后调用）"""
        self._diff_panel = panel

    def _open_diff_panel(self):
        """打开代码修改实时面板"""
        panel = getattr(self, '_diff_panel', None)
        if panel is not None:
            panel.show_panel()

    def _drain_queue(self):
        """批量收集 → 一次性 insertHtml（含二次去重安全网）"""
        lines = []
        seen = set()  # 本轮去重
        while len(lines) < 200:
            try:
                line = _log_queue.get_nowait()
            except queue.Empty:
                break
            # 二次去重：基于内容hash，防止_enqueue漏掉的重复
            line_hash = hash(line)
            if line_hash in seen:
                continue
            seen.add(line_hash)
            lines.append(line)

        if not lines:
            return

        # 🎤 Agent 内容朗读：在 QTimer 事件循环里检测（不在 loguru emit 链中，
        # 内部 logger 调用安全，杜绝 sink 重入死锁）
        try:
            for line in lines:
                _maybe_speak_agent_line(line)
        except Exception:
            pass

        self._total_lines += len(lines)
        self._line_count.setText(f"{self._total_lines} 行")

        html_parts = []
        for line in lines:
            # 🔒 超长行截断显示（多 KB 的 Agent 回复整行高亮+渲染会卡主线程）
            if len(line) > 2000:
                line = line[:2000] + f"  …（已截断，原 {len(line)} 字符）"
            highlighted = _highlight_line(line)
            html_parts.append(
                f'<div style="line-height:1.55;white-space:pre-wrap;'
                f'font-family:\'Cascadia Code\',\'Fira Code\',Consolas,'
                f'monospace;font-size:12px;">{highlighted}</div>'
            )

        batch_html = ''.join(html_parts)

        # beginEditBlock: 批量插入只触发一次 re-layout，性能提升 10~100x
        doc = self._output.document()
        cursor = self._output.textCursor()
        cursor.beginEditBlock()
        try:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertHtml(batch_html)
        finally:
            cursor.endEditBlock()

        if self._auto_scroll:
            sb = self._output.verticalScrollBar()
            sb.setValue(sb.maximum())

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)


# 🎤 模块级显式注册控制台朗读（不依赖 install_all 的锁检查，防静默漏注册）
try:
    init_console_tts()
except Exception as e:
    logger.warning("[TTS-Console] 模块级注册失败: {}: {}", type(e).__name__, e)
