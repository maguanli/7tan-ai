# -*- coding: utf-8 -*-
"""
爆款写作插件 — 授权模块（付费插件核心）

机制：
  1. RSA-2048 签名授权码：作者持有私钥（private_key.pem，不公开），
     本文件内嵌公钥。授权码 = 机器指纹 + RSA 签名。
     开源后公钥公开也没关系 —— 没有私钥就无法伪造授权码。
  2. 授权码绑定机器指纹（MAC + 主机名 + 平台），换机需联系作者重新发码。
  3. 未激活用户可免费试用 TRIAL_LIMIT 次，之后必须激活才能继续使用。

用法（在 tools.py 中）：
  from license 模块 import check_access
  ok, msg = check_access()
  if not ok: return msg
"""
import os
import base64
import hashlib
import json
import platform
import socket
import time
import uuid
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# ─── 公钥（公开无妨；私钥在作者手里，见 private_key.pem）───
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAlczI6cF/6iFpz4KE1CsN
7STxE+FSPvwLIu8eHe+/yayK3LaiOqZsz/1tB0awQTLuoe0G4gBp8JQGM3f5DvJA
kSIRP3G3bYla6FCSFIWU7ClG0IKwBzGIqcIrDaqxdSgRlNDEsc3LqDCAy0HtvJDC
aDAvtjsysV3LmlWaTdNh+aMAh3t1AFDvLYI89ISC/kLB+Hx4joBA4DDDGLxmk0ZN
kY7BAeV+bfzsOXpB5Kxb+bovPx2niQHHjrF6gzXqu9QAQaNyPso/KHKr2AR2iCyr
ETNqpPR1Cly5wE3dSPMNauxRzWjIbICSRbdQVtqzwYnj32Ko8m2HFfvfAhi1nNag
MQIDAQAB
-----END PUBLIC KEY-----"""

# ─── 免费试用次数（未激活用户）───
TRIAL_LIMIT = 5

# ─── 购买引导文案（作者可修改：价格 / 联系方式）───
PURCHASE_INFO = (
    "💳 爆款写作插件为付费插件\n"
    f"   • 免费试用 {TRIAL_LIMIT} 次，之后需要授权码激活\n"
    "   • 价格：50 元/台（永久授权，绑定当前电脑）\n"
    "   • 购买方式：在线购买，余额付款秒发授权码\n"
    "   • 购买页面：https://www.7tan.com/pro.php\n"
    "   • 流程：登录 → 粘贴机器指纹 → 余额购买 → 复制授权码\n"
    "   • 余额不足先去充值：https://www.7tan.com/task/wallet.php\n"
    "   • 换机 / 重装系统可联系作者免费补发\n"
    "   • 获取授权码后，用 viral_activate 输入即可激活\n"
)

# ─── 状态文件（激活状态 + 试用计数）───
_STATE_FILE = Path(__file__).resolve().parent / "state.json"
# ─── 激活凭证双保险备份 ───
# ① 同目录备份：防 state.json 被误删/损坏
_BACKUP_FILE = Path(__file__).resolve().parent / "state_backup.json"
# ② 全局备份：防整个插件目录被清理/重装（cwd 为项目根时有效）
_GLOBAL_BACKUP_FILE = (
    Path.cwd() / "data" / "backups" / "plugin_states" / "viral_writer_state.json"
)
# ─── 私钥路径（仅作者发码环境需要；客户端包不含私钥）───
# 优先级：环境变量 VIRAL_WRITER_PRIVATE_KEY > 作者本机 ~/.7tan_keys/ > 插件目录（旧路径兼容）
def _resolve_private_key_file():
    env = os.environ.get("VIRAL_WRITER_PRIVATE_KEY", "")
    if env and Path(env).exists():
        return Path(env)
    home_keys = Path.home() / ".7tan_keys" / "viral_writer_private_key.pem"
    if home_keys.exists():
        return home_keys
    return Path(__file__).resolve().parent / "private_key.pem"

_PRIVATE_KEY_FILE = _resolve_private_key_file()

# ─── 工具函数 ───

def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def get_fingerprint() -> str:
    """机器指纹：MAC + 主机名 + 平台信息 → sha256 前 32 位"""
    parts = []
    try:
        mac = uuid.getnode()
        parts.append(f"mac:{mac:x}")
    except Exception:
        pass
    try:
        parts.append(f"host:{socket.gethostname()}")
    except Exception:
        pass
    try:
        parts.append(f"node:{platform.node()}")
        parts.append(f"plat:{platform.system()}-{platform.release()}")
    except Exception:
        pass
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _load_public_key():
    return serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode())


def _load_private_key():
    """仅作者本机存在私钥时可用（发码工具用）"""
    if not _PRIVATE_KEY_FILE.exists():
        return None
    return serialization.load_pem_private_key(
        _PRIVATE_KEY_FILE.read_bytes(), password=None
    )


def gen_license(fingerprint: str = None) -> str:
    """生成授权码（作者用）。返回 '指纹.签名' 格式。"""
    priv = _load_private_key()
    if priv is None:
        raise RuntimeError("私钥不存在（本机不是授权码签发环境）")
    fp = fingerprint or get_fingerprint()
    sig = priv.sign(fp.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    return f"{fp}.{_b64u(sig)}"


def verify_key(license_key: str):
    """验证授权码。返回 (ok, 指纹, 错误信息)"""
    key = (license_key or "").strip()
    if "." not in key:
        return False, "", "授权码格式不正确"
    fp, sig_b64 = key.rsplit(".", 1)
    if len(fp) != 32:
        return False, "", "授权码格式不正确"
    try:
        sig = _b64u_decode(sig_b64)
        pub = _load_public_key()
        pub.verify(sig, fp.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        return True, fp, ""
    except InvalidSignature:
        return False, "", "授权码无效（签名校验失败）"
    except Exception as e:
        return False, "", f"授权码校验异常: {e}"


# ─── 状态管理 ───

def _write_state_file(path: Path, data: str):
    """安全写状态文件（目录不存在自动创建，失败静默）"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
    except Exception:
        pass


def _load_state() -> dict:
    default = {"activated": False, "license": "", "activated_at": "", "trial_used": 0}
    candidates = [_STATE_FILE, _BACKUP_FILE, _GLOBAL_BACKUP_FILE]
    for f in candidates:
        try:
            if f.exists():
                st = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(st, dict):
                    # 从任一位置读到有效状态 → 自动恢复/同步到所有位置
                    _save_state(st)
                    return st
        except Exception:
            continue
    return default


def _save_state(state: dict):
    data = json.dumps(state, ensure_ascii=False, indent=2)
    # ① 主文件
    _write_state_file(_STATE_FILE, data)
    # ② 同目录备份（防主文件误删/损坏）
    _write_state_file(_BACKUP_FILE, data)
    # ③ 全局备份（防整个插件目录被清理/重装；cwd 下无 data 目录则跳过）
    if Path.cwd().joinpath("data").is_dir():
        _write_state_file(_GLOBAL_BACKUP_FILE, data)


def is_activated() -> bool:
    st = _load_state()
    if not st.get("activated"):
        return False
    # 激活后仍校验签名 + 指纹（防止改 state.json 伪造）
    ok, fp, _ = verify_key(st.get("license", ""))
    if not ok:
        return False
    return fp == get_fingerprint()


def activate(license_key: str):
    """激活插件。返回 (ok, 消息)"""
    ok, fp, err = verify_key(license_key)
    if not ok:
        return False, f"❌ {err}"
    if fp != get_fingerprint():
        return False, "❌ 授权码与当前电脑不匹配（授权码绑定购买时的机器）"
    st = _load_state()
    st["activated"] = True
    st["license"] = license_key.strip()
    st["activated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_state(st)
    return True, "✅ 激活成功！爆款写作全部功能已解锁，永久使用。"


def deactivate():
    st = _load_state()
    st["activated"] = False
    st["license"] = ""
    _save_state(st)


# ─── 试用 ───

def trial_left() -> int:
    if is_activated():
        return -1  # 已激活，无试用限制
    st = _load_state()
    used = int(st.get("trial_used", 0))
    return max(0, TRIAL_LIMIT - used)


def _consume_trial() -> bool:
    """消耗一次试用。返回是否允许使用"""
    if is_activated():
        return True
    st = _load_state()
    used = int(st.get("trial_used", 0))
    if used >= TRIAL_LIMIT:
        return False
    st["trial_used"] = used + 1
    _save_state(st)
    return True


# ─── 统一访问闸门 ───

def check_access():
    """工具调用前的统一检查。返回 (allowed, 消息)"""
    if is_activated():
        return True, ""
    left = trial_left()
    if left > 0:
        if _consume_trial():
            return True, f"（免费试用剩余 {left - 1} 次）"
        return True, ""
    return False, (
        f"🚫 爆款写作插件免费试用已用完（{TRIAL_LIMIT} 次）。\n"
        f"{PURCHASE_INFO}"
    )


def status_text() -> str:
    """查看激活状态 / 试用剩余 / 购买信息"""
    if is_activated():
        st = _load_state()
        return (
            "✅ 爆款写作插件：已激活（永久）\n"
            f"   • 激活时间：{st.get('activated_at', '')}\n"
            "   • 绑定机器指纹：已绑定当前电脑\n"
        )
    left = trial_left()
    lines = [
        "🔓 爆款写作插件：未激活",
        f"   • 免费试用剩余：{left} 次",
        f"   • 本机指纹：{get_fingerprint()}（发授权码时请提供）",
    ]
    if left <= 0:
        lines.append("")
        lines.append(PURCHASE_INFO)
    return "\n".join(lines)
