# -*- coding: utf-8 -*-
"""全局语音朗读桥：让任何 Agent 调用（聊天页 / 工作台 / 流水线任务）都能朗读最终回复。

- 应用启动时注册一次；回调内部实时读取数据库 voice_mode 开关，关闭语音时自动静音。
- 与聊天页 _speak_response 共享 tts_speak_dedup 全局去重，多通道同时触发也只出声一次。
"""
import logging
import sqlite3

from loguru import logger as lgr

logger = logging.getLogger(__name__)


def _voice_mode_enabled() -> bool:
    """从数据库 app_settings 读取 voice_mode（'true'=语音朗读开启）"""
    try:
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
    except Exception as e:
        logger.debug(f"[TTS-Bridge] 读取 voice_mode 失败: {e}")
        return False


def _get_voice_gender() -> str:
    """从数据库 app_settings 读取 voice_gender（'female'/'male'，非法值返回空串）"""
    try:
        from src.database.db import _get_data_dir
        db_path = _get_data_dir() / "games.db"
        con = sqlite3.connect(str(db_path), timeout=3)
        try:
            cur = con.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)"
            )
            cur.execute("SELECT value FROM app_settings WHERE key='voice_gender'")
            row = cur.fetchone()
            g = str(row[0]).strip().lower() if row else ""
            return g if g in ("female", "male") else ""
        finally:
            con.close()
    except Exception as e:
        logger.debug(f"[TTS-Bridge] 读取 voice_gender 失败: {e}")
        return ""


def _global_tts_callback(text: str) -> None:
    """全局朗读回调：voice_mode 开启时才朗读（共享全局去重防重复）"""
    if not _voice_mode_enabled():
        lgr.info("[TTS-Bridge] 语音开关关闭，跳过朗读")
        return
    try:
        from data.plugins.tts_piper.tools import tts_speak_dedup, tts_set_gender
        # 🎤 朗读前同步性别：确保用数据库最新 voice_gender（WEB 版切换性别只写数据库，
        # TTS 模块内存 _voice_gender 默认 female，不同步会导致"男女切换不生效"）
        _g = _get_voice_gender()
        lgr.info(f"[TTS-Bridge] Agent 回复朗读触发：gender={_g or 'default'} 文本长度={len(text or '')}")
        if _g:
            tts_set_gender(_g)
        tts_speak_dedup(text or "")
    except Exception as e:
        lgr.warning(f"[TTS-Bridge] 全局朗读失败: {e}")


def init_global_tts() -> None:
    """注册全局朗读回调（应用启动时调用一次，幂等）"""
    try:
        from src.agent.agent_loop import register_agent_speak_callback
        register_agent_speak_callback(_global_tts_callback)
        print("[TTS-Bridge] 全局语音朗读已注册（voice_mode 开关生效）")
        logger.info("[TTS-Bridge] 全局语音朗读已注册（voice_mode 开关生效）")
        lgr.info("[TTS-Bridge] 全局语音朗读已注册（voice_mode 开关生效）")
    except Exception as e:
        print(f"[TTS-Bridge] 注册失败: {e}")
        logger.warning(f"[TTS-Bridge] 注册失败: {e}")
        lgr.warning(f"[TTS-Bridge] 注册失败: {e}")


def interrupt_speaking(reason: str = "") -> dict:
    """立即打断正在进行的朗读（用户发送新消息时调用）。

    顺序至关重要：
      1. 先清空各控制台通道的待读缓冲 —— 否则 tts_stop() 触发的“播放完成回调”
         会把暂存的旧内容又补读一遍（防漏读机制的反作用）；
      2. 再 tts_stop() —— 通知播放线程立即停止当前音频 + 清空播放队列。

    ⚠️ 本函数会被 Web 请求线程（asyncio 事件循环）直接调用，**必须快速返回**。
    历史事故（2026-09-13）：tts_stop() 内部直接调用 winsound.PlaySound(None, SND_PURGE)，
    而该调用会阻塞到音频自然播完（实测 60 秒音频阻塞 58 秒）→ 整个 Web 服务卡死
    → 前端 12 秒超时 → 误弹「网页版服务未运行」。tts_stop() 已改为非阻塞的
    「置位中断标记」，此处再加一道耗时告警兜底。

    只处理“已加载”的通道（sys.modules 判定）：未加载说明该通道从未发声，
    无需打断；同时避免在 WEB 进程里误导入 PyQt6（console_panel）产生副作用。
    """
    import sys
    import time as _time

    _t0 = _time.monotonic()
    cleared = []

    # 1. 清空各通道待读缓冲（必须先于 tts_stop，防打断后被补读）
    for mod_name, fn_name in (
        ("src.ui.console_panel", "reset_console_speech_state"),
        ("src.agent.web_console_tts", "reset_web_console_speech_state"),
    ):
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        fn = getattr(mod, fn_name, None)
        if not callable(fn):
            continue
        try:
            fn()
            cleared.append(fn_name)
        except Exception as e:
            logger.warning(f"[TTS-Bridge] 清空待读缓冲失败({mod_name}): {e}")

    # 2. 停止播放：清空播放队列 + 打断当前音频
    tools = sys.modules.get("data.plugins.tts_piper.tools")
    if tools is not None:
        try:
            tools.tts_stop()
            cleared.append("tts_stop")
        except Exception as e:
            logger.warning(f"[TTS-Bridge] 停止播放失败: {e}")

    _el = _time.monotonic() - _t0
    if _el > 2.0:
        logger.warning(
            f"[TTS-Bridge] ⚠️ 打断朗读耗时过长 {_el:.1f}s（禁止在请求/事件循环线程调用阻塞式音频 API！）"
        )
    lgr.info(
        f"[TTS-Bridge] 已打断上一次朗读（触发={reason or 'unknown'}，耗时={_el:.3f}s，清理={cleared if cleared else '无'}）"
    )
    return {"status": "ok", "cleared": cleared, "elapsed": round(_el, 3)}
