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
