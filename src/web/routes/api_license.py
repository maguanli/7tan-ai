"""
授权状态 API — 完整版（Pro）激活状态

GET /api/license/status — 返回当前授权等级（RSA 验签，防伪造）
"""
from fastapi import APIRouter
from loguru import logger

router = APIRouter(prefix="/api/license", tags=["license"])


@router.get("/status")
async def license_status():
    """返回授权状态：is_pro / level / message

    逻辑与 src/core/score.py 保持一致：
    声称 pro/enterprise 必须有 RSA 验签通过的 pro_license，否则降级为 free。
    """
    try:
        from src.security.token_store import load_token
        from src.security.license_verify import verify_license, LicenseError

        token_data = load_token()
        if not token_data:
            return {"is_pro": False, "level": "free", "message": "未登录（免费版）"}

        level = token_data.get("level", "free")
        pro_license = token_data.get("pro_license") or ""

        if level in ("pro", "enterprise"):
            if pro_license:
                try:
                    result = verify_license(pro_license)
                    if result.get("level") == "pro":
                        return {
                            "is_pro": True,
                            "level": "pro",
                            "message": "完整版已激活 ✓",
                        }
                except LicenseError:
                    # RSA 验签失败 → level 可能被篡改，降级
                    logger.warning("[License] RSA 验签失败，level 可能被篡改，降级为 free")
                    level = "free"
            else:
                # 声称 pro 但没有 license → 必须是 HMAC 校验通过的旧版 token
                if not token_data.get("_hmac_ok", False):
                    logger.warning("[License] 声称 pro 但无 license 且 HMAC 失败，降级为 free")
                    level = "free"

        is_pro = level in ("pro", "enterprise")
        return {
            "is_pro": is_pro,
            "level": level,
            "message": "完整版已激活 ✓" if is_pro else "当前为免费版",
        }
    except Exception as e:
        logger.error(f"license status 查询失败: {e}")
        return {"is_pro": False, "level": "unknown", "message": "授权状态不可用"}
