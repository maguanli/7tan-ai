# -*- coding: utf-8 -*-
"""WEB 版实时控制台朗读：监听标准 logging 的 💬 Agent 日志行 → 后台 TTS 朗读。

背景：桌面版通过 src/ui/console_panel.py 的 _maybe_speak_agent_line 监听
标准 logging 输出中的 "💬 Agent:" 行（中间迭代截断内容 + 最终完整回复）
并朗读。该模块是 PyQt6 UI 组件，WEB 版（pythonw / uvicorn 进程）无法使用，
导致 WEB 版实时控制台中的 💬 Agent 说话内容没有语音朗读。

本模块提供无 UI 依赖的等价实现（纯 threading + loguru + tts_piper 插件），
行为与桌面版一致：
  - 中间迭代截断输出（`content[:100]...`）→ 2 秒合并窗口，最新一条朗读
  - 最终完整回复（无省略号）→ 立即朗读，并取消待读截断内容
  - 防重复 / 防叠加：复用 tts_speak_dedup / tts_is_spoken / tts_is_busy
  - 播放中不丢弃：暂存最新一条，播放完成回调自动补读（防漏读）

启动时调用 init_web_console_tts()（幂等），安装标准 logging Handler。
"""
import logging
import re
import threading

from loguru import logger as lgr

_AGENT_LINE_RE = re.compile(r"💬\s*Agent:\s*(.+)$", re.S)

_web_handler_installed = False

# —— 截断行(中间迭代)朗读：最新优先 + 2 秒合并窗口 ——
_trunc_pending_text = None
_trunc_pending_timer = None
_trunc_lock = threading.Lock()

# —— 播放中暂存（最新一条），播放完成自动补读 ——
_pending_speak = None
_pending_speak_lock = threading.Lock()


def _voice_mode_enabled() -> bool:
    """从数据库 app_settings 读取 voice_mode（与 speak_bridge 共用逻辑）"""
    try:
        from src.agent.speak_bridge import _voice_mode_enabled as _v
        return _v()
    except Exception:
        try:
            import sqlite3
            from src.database.db import _get_data_dir
            db_path = _get_data_dir() / "games.db"
            con = sqlite3.connect(str(db_path), timeout=3)
            try:
                cur = con.cursor()
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)"
                )
                cur.execute("SELECT value FROM app_settings WHERE key='voice_mode'")
                row = cur.fetchone()
                return bool(row) and str(row[0]).strip().lower() == "true"
            finally:
                con.close()
        except Exception:
            return False


def _get_voice_gender() -> str:
    try:
        from src.agent.speak_bridge import _get_voice_gender as _g
        return _g()
    except Exception:
        return ""


def _set_pending_speak(text: str) -> None:
    global _pending_speak
    with _pending_speak_lock:
        _pending_speak = text


def _take_pending_speak():
    global _pending_speak
    with _pending_speak_lock:
        t = _pending_speak
        _pending_speak = None
    return t


def _clear_pending_speak() -> None:
    global _pending_speak
    with _pending_speak_lock:
        _pending_speak = None


def _speak_agent(text: str) -> None:
    """后台朗读一段 Agent 文本（防重复 + 播放中暂存补读 + 全链路日志）"""
    if not text or not text.strip():
        return

    def _do():
        try:
            if not _voice_mode_enabled():
                lgr.info("[TTS-Web] 语音模式关闭，跳过朗读")
                return
            from data.plugins.tts_piper.tools import (
                tts_speak_dedup, tts_is_busy, tts_is_spoken,
            )
            # 已在去重窗口内朗读过 → 跳过
            if tts_is_spoken(text):
                lgr.info("[TTS-Web] 该内容已朗读过（去重窗口内），跳过")
                return
            # 正在播放 → 暂存最新一条，播完自动补读（防漏读）
            if tts_is_busy():
                _set_pending_speak(text)
                lgr.info("[TTS-Web] 正在播放中，暂存待补读（最新一条）")
                return
            lgr.info("[TTS-Web] 🔊 开始朗读 Agent 回复（{}字）", len(text))
            r = tts_speak_dedup(text)
            if r.get("skipped"):
                msg = r.get("message", "?")
                if "互斥" in msg or "合成" in msg:
                    _set_pending_speak(text)
                    lgr.info("[TTS-Web] 合成互斥，暂存待补读（{}）", msg)
                else:
                    lgr.info("[TTS-Web] 朗读被全局去重拦截（{}），跳过", msg)
                return
            if r.get("status") == "ok":
                lgr.info(
                    "[TTS-Web] 朗读完成: engine={} size={}KB",
                    r.get("engine", "?"), r.get("size_kb", "?"),
                )
            else:
                lgr.warning("[TTS-Web] 朗读失败: {}", r.get("message", "?"))
        except Exception as e:
            lgr.warning("[TTS-Web] 朗读异常: {}: {}", type(e).__name__, e)

    threading.Thread(target=_do, daemon=True).start()


def _flush_trunc_pending() -> None:
    """合并窗口到期：朗读暂存的最新截断内容（最新优先，只读一条）"""
    global _trunc_pending_text, _trunc_pending_timer
    with _trunc_lock:
        text = _trunc_pending_text
        _trunc_pending_text = None
        _trunc_pending_timer = None
    if text:
        # 去掉尾部省略号再朗读（避免读成"点点点"）
        clean = text[:-3].rstrip() if text.endswith("...") else text
        if clean:
            lgr.info("[TTS-Web] 🔊 朗读 Agent 实时内容（{}字）", len(clean))
            _speak_agent(clean)


def _cancel_trunc_pending() -> None:
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
    _clear_pending_speak()


def _maybe_speak_agent_line(line: str) -> None:
    """检测 💬 Agent 日志行 → 后台朗读（与桌面版 console_panel 行为一致）

    - 中间迭代截断输出（`content[:100]...`）→ 2 秒合并窗口，最新一条朗读
    - 最终完整回复（无省略号）→ 立即朗读，并取消待读截断内容
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
        with _trunc_lock:
            _trunc_pending_text = content
            if _trunc_pending_timer is None:
                _trunc_pending_timer = threading.Timer(2.0, _flush_trunc_pending)
                _trunc_pending_timer.daemon = True
                _trunc_pending_timer.start()
        lgr.debug("[TTS-Web] Agent 实时内容已收录（{}字，稍后朗读）", len(content))
        return
    # 最终完整回复：优先朗读
    _cancel_trunc_pending()
    lgr.info("[TTS-Web] 检测到 Agent 完整回复，触发朗读（{}字）", len(content))
    _speak_agent(content)


class _AgentLineLoggingHandler(logging.Handler):
    """标准 logging → 💬 Agent 行朗读（异步线程，不阻塞 emit 链）"""

    def emit(self, record):
        try:
            msg = record.getMessage()
            if "💬 Agent:" not in msg:
                return
            if not _AGENT_LINE_RE.search(msg):
                return
            # 异步处理：不阻塞 logging emit 链（防与 loguru sink 争锁死锁）
            threading.Thread(
                target=_maybe_speak_agent_line, args=(msg,), daemon=True
            ).start()
        except Exception:
            pass


def _on_play_finished() -> None:
    """播放完成回调：若播放队列空闲且有暂存内容 → 自动补读（防漏读）"""
    try:
        from data.plugins.tts_piper.tools import tts_is_busy
        if tts_is_busy():
            return
        text = _take_pending_speak()
        if text:
            lgr.info("[TTS-Web] ▶ 播放完成，补读暂存内容（{}字）", len(text))
            _speak_agent(text)
    except Exception as e:
        lgr.warning("[TTS-Web] 补读回调异常: {}: {}", type(e).__name__, e)


def init_web_console_tts() -> None:
    """安装 WEB 版实时控制台朗读监听（幂等；WEB server 启动时调用一次）"""
    global _web_handler_installed
    if _web_handler_installed:
        return
    _web_handler_installed = True
    try:
        # 1. 安装标准 logging Handler：监听 💬 Agent 日志行
        handler = _AgentLineLoggingHandler()
        handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(handler)
        # 2. 播放完成回调：空闲时补读忙碌暂存内容（防漏读）
        try:
            from data.plugins.tts_piper.tools import register_tts_finish_callback
            register_tts_finish_callback(_on_play_finished)
        except Exception as _cb_err:
            lgr.debug("[TTS-Web] 补读回调注册失败: {}", _cb_err)
        lgr.info("[TTS-Web] 💬 Agent 日志行朗读监听已安装（WEB 实时控制台）")
    except Exception as e:
        _web_handler_installed = False
        lgr.warning("[TTS-Web] 安装失败: {}: {}", type(e).__name__, e)
