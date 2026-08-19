"""
启动登录门卫（P2-8）— 登录编排核心逻辑

将「Token 检查 → 登录对话框 → 用户信息组装 → 设备指纹上报」整体编译为
entry_auth.pyd（机器码），防止破解者通过反编译 patch 掉登录检查直接进入主界面。

- 所有核心判断都在 pyd 内部完成
- app.py 仅保留薄封装调用（即使被 patch，门卫逻辑依然在机器码中）
- 登录失败/取消 → 返回 None，主程序退出
"""
import logging

logger = logging.getLogger("entry_auth")


def perform_login_gate() -> dict | None:
    """
    登录门卫（编译进 pyd，防 patch 跳过登录检查）

    Returns:
        user_info dict（含 token/username/level/pro_expires/pro_license），
        用户取消登录或 token 缺失时返回 None（调用方应退出应用）。
    """
    try:
        from ..security.token_store import is_token_available, load_token
        from ..ui.login_dialog import show_login_dialog

        user_info = None

        # ===== 1. 本地 Token 检查 =====
        if is_token_available():
            data = load_token()
            if data:
                user_info = {
                    "token": data.get("token", ""),
                    "username": data.get("username", ""),
                    "level": data.get("level", "free"),
                    "pro_expires": data.get("pro_expires", 0),
                    "pro_license": data.get("pro_license") or "",
                }
                logger.info(f"[Login] 使用本地 Token (用户: {user_info['username']})")

        # ===== 2. 无 Token → 显示登录对话框 =====
        if user_info is None:
            logger.info("[Login] 显示登录对话框...")
            user_info = show_login_dialog()

        # ===== 3. 用户取消登录 → 退出 =====
        if user_info is None:
            logger.info("[Login] 用户取消登录，退出")
            return None

        # ===== 4. 完整性校验：登录结果必须携带有效 token =====
        token = user_info.get("token") or ""
        if not token or len(token) < 20:
            logger.warning("[Login] 登录结果缺少有效 token，视为未登录")
            return None

        # ===== 5. 设备指纹：本地烙印记 + 服务器多设备检测（静默，不阻塞）=====
        try:
            from ..security.device_fingerprint import on_login as _fp_on_login
            _fp_on_login(user_info)
        except Exception:
            pass

        return user_info

    except Exception:
        logger.exception("[Login] 登录门卫异常")
        raise
