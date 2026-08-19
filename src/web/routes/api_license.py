"""
授权状态 API — 完整版（Pro）激活状态

GET  /api/license/status   — 返回授权等级 + 用户名 + 能力值（RSA 验签，防伪造）
POST /api/license/login    — 登录 7tan.com（复用桌面版 auth_client）
POST /api/license/refresh  — 刷新会员 Token 状态
POST /api/license/logout   — 退出登录（清除本地 Token）
"""
import os
from pathlib import Path

from fastapi import APIRouter, Request
from loguru import logger

router = APIRouter(prefix="/api/license", tags=["license"])

# 项目根目录（src/web/routes/api_license.py → parents[3] = 项目根）
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _ensure_project_root():
    """确保进程 cwd 为项目根目录。

    token_store 用相对路径 data/auth/token.dat，依赖 cwd。若 WEB 进程
    cwd 与桌面版不一致，会读不到登录态。这里强制对齐。
    """
    try:
        if os.getcwd() != str(_PROJECT_ROOT):
            os.chdir(str(_PROJECT_ROOT))
    except Exception:
        pass


def _resolve_status():
    """返回 (is_pro, level, message, username)。

    逻辑与 src/core/score.py 保持一致：
    声称 pro/enterprise 必须有 RSA 验签通过的 pro_license，否则降级为 free。
    """
    _ensure_project_root()
    from src.security.token_store import load_token
    from src.security.license_verify import verify_license, LicenseError

    token_data = load_token()
    username = (token_data or {}).get("username", "") or ""
    if not token_data:
        return False, "free", "未登录（免费版）", username

    level = token_data.get("level", "free")
    pro_license = token_data.get("pro_license") or ""

    if level in ("pro", "enterprise"):
        if pro_license:
            try:
                result = verify_license(pro_license)
                if result.get("level") == "pro":
                    return True, "pro", "完整版已激活 ✓", username
            except LicenseError:
                logger.warning("[License] RSA 验签失败，level 可能被篡改，降级为 free")
                level = "free"
        else:
            # 声称 pro 但没有 license → 必须是 HMAC 校验通过的旧版 token
            if not token_data.get("_hmac_ok", False):
                logger.warning("[License] 声称 pro 但无 license 且 HMAC 失败，降级为 free")
                level = "free"

    is_pro = level in ("pro", "enterprise")
    return is_pro, level, ("完整版已激活 ✓" if is_pro else "当前为免费版"), username


def _compute_score():
    """计算能力值（可能较慢，失败返回空）。"""
    try:
        from src.core.score import auto_evaluate, format_score_brief
        result = auto_evaluate()
        return {
            "score": round(result.get("composite_score", 0), 1),
            "brief": format_score_brief(result),
        }
    except Exception as e:
        logger.warning(f"[License] 能力值计算失败: {e}")
        return {"score": 0, "brief": ""}


@router.get("/status")
def license_status():
    """返回授权状态：is_pro / level / message / username / score / score_brief"""
    try:
        is_pro, level, message, username = _resolve_status()
        score = _compute_score()
        return {
            "is_pro": is_pro,
            "level": level,
            "message": message,
            "username": username,
            "score": score.get("score", 0),
            "score_brief": score.get("brief", ""),
        }
    except Exception as e:
        logger.error(f"license status 查询失败: {e}")
        return {
            "is_pro": False,
            "level": "unknown",
            "message": "授权状态不可用",
            "username": "",
            "score": 0,
            "score_brief": "",
        }


@router.post("/login")
async def license_login(request: Request):
    """登录 7tan.com（复用桌面版 auth_client.login 的完整链路）。

    请求体: {"username": "xxx", "password": "xxx", "remember": true}
    """
    _ensure_project_root()
    try:
        body = await request.json()
    except Exception:
        return {"success": False, "message": "请求体格式错误，需 JSON"}

    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    remember = bool(body.get("remember", False))

    if not username:
        return {"success": False, "message": "请输入用户名或手机号"}
    if not password:
        return {"success": False, "message": "请输入密码"}

    try:
        from src.security.auth_client import (
            login, LoginFailed, NetworkError, ServerError,
        )
        from src.security.token_store import save_token
        from src.security.device_fingerprint import on_login as device_fp_on_login

        result = login(username, password, remember_me=remember)
        save_token(
            token=result.get("token") or "",
            username=result.get("username") or "",
            level=result.get("level") or "free",
            pro_expires=result.get("pro_expires", 0),
            expires_in=result.get("expires_in", 2592000),
            trial_ai_count=result.get("trial_ai_count", 0),
            pro_license=result.get("pro_license") or "",
        )
        try:
            device_fp_on_login(result)
        except Exception:
            pass
        try:
            from src.tools.registry import invalidate_pro_cache
            invalidate_pro_cache()
        except Exception:
            pass
        logger.info(f"[License] WEB 登录成功: {result.get('username')} (等级: {result.get('level')})")
        return {
            "success": True,
            "message": "登录成功",
            "username": result.get("username", ""),
            "level": result.get("level", "free"),
        }
    except LoginFailed as e:
        return {"success": False, "message": str(e)}
    except NetworkError as e:
        return {"success": False, "message": str(e)}
    except ServerError as e:
        _msg = str(e)
        # 编译版 auth_client 对 7tan.com 的 401 无法解析中文 message，统一转为友好提示
        if "401" in _msg or "未授权" in _msg:
            _msg = "账号或密码错误（7tan.com 拒绝登录），请检查账号密码是否正确"
        return {"success": False, "message": _msg}
    except Exception as e:
        logger.error(f"[License] 登录失败: {e}")
        return {"success": False, "message": f"登录失败: {e}"}


@router.post("/refresh")
def license_refresh():
    """刷新会员 Token 状态（与桌面版「🔄 刷新」按钮逻辑一致）。"""
    _ensure_project_root()
    try:
        from src.security.token_store import load_token, save_token
        from src.security.auth_client import refresh_token

        token_data = load_token()
        if not token_data or not token_data.get("token"):
            return {"success": False, "message": "未找到登录信息，请重新登录"}

        result = refresh_token(token_data["token"])
        if not result.get("success"):
            return {"success": False, "message": result.get("message", "刷新失败，请检查网络后重试")}

        new_token = result.get("token", token_data["token"])
        new_info = {
            **token_data,
            "token": new_token,
            "level": result.get("level", "free"),
            "pro_expires": result.get("pro_expires", 0),
            "pro_license": result.get("pro_license") or "",
        }
        save_token(
            token=new_info["token"],
            username=new_info.get("username", ""),
            level=new_info.get("level") or "free",
            pro_expires=new_info.get("pro_expires", 0),
            expires_in=new_info.get("expires_in", 2592000),
            pro_license=new_info.get("pro_license") or "",
        )
        try:
            from src.tools.registry import invalidate_pro_cache
            invalidate_pro_cache()
        except Exception:
            pass
        logger.info("[License] Token 刷新成功")
        return {"success": True, "message": "会员状态已更新！"}
    except Exception as e:
        logger.error(f"license refresh 失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/logout")
def license_logout():
    """退出登录（清除本地 Token）。"""
    _ensure_project_root()
    try:
        from src.security.token_store import clear_token
        clear_token()
        try:
            from src.tools.registry import invalidate_pro_cache
            invalidate_pro_cache()
        except Exception:
            pass
        logger.info("[License] 用户已退出登录")
        return {"success": True, "message": "已退出登录"}
    except Exception as e:
        logger.error(f"license logout 失败: {e}")
        return {"success": False, "message": str(e)}
