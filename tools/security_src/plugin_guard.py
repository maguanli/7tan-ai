"""
插件完整性守卫 — 内置插件 SHA-256 白名单 + HMAC 签名校验
编译为 .pyd 后 HMAC 密钥无法被提取；防止插件 tools.py 被篡改后重打包分发。

白名单文件: data/plugins/hashes.json
格式: {"plugins": {"plugin_id": "sha256hex", ...}, "sig": "hmac_sha256_hex"}
"""
import base64
import hashlib
import hmac
import importlib.util
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_KEY_PART1 = b'\x3a\x7f\x2c\x91\xe4\xb8\x55\x0d\xc6\xd2\x88\xfe\x17\xa3\x4b\x69'
_KEY_PART2 = b'\x8b\x1e\x5f\xc3\x22\xd7\x9a\x40\xee\x61\x3d\xb5\xf9\x04\x7c\xa6'
_NONCE_PREFIX = b'\x7f\x4a\x2e\x91'
# 构建时由 tools/gen_plugin_guard.py 注入：AES-256-GCM 加密的 32 字节 HMAC 密钥
_HMAC_ENC = "__HMAC_ENC__"


def _assemble_key() -> bytes:
    return _KEY_PART1 + _KEY_PART2


def _decrypt(encrypted_b64: str) -> bytes:
    """解密 AES-GCM 密文，返回明文 bytes"""
    if not encrypted_b64:
        return b""
    try:
        raw = base64.b64decode(encrypted_b64)
    except Exception:
        return b""
    if len(raw) < 12:
        return b""
    try:
        return AESGCM(_assemble_key()).decrypt(raw[:12], raw[12:], None)
    except Exception:
        return b""


def _hmac_key() -> bytes:
    """解密返回 HMAC-SHA256 密钥（不落盘，每次调用解密）"""
    key = _decrypt(_HMAC_ENC)
    if not key:
        raise RuntimeError("插件白名单密钥不可用")
    return key


def sign_hashes(canonical_json: str) -> str:
    """生成白名单签名（构建工具 tools/gen_plugin_hashes.py 调用）"""
    return hmac.new(_hmac_key(), canonical_json.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_sig(canonical_json: str, sig: str) -> bool:
    """验证白名单签名（防篡改 hashes.json 本身）"""
    if not sig:
        return False
    try:
        expected = sign_hashes(canonical_json)
    except Exception:
        return False
    return hmac.compare_digest(expected, sig.strip().lower())


def _bundled_whitelist_path() -> "Path | None":
    """PyInstaller 打包内置白名单位置（_internal/data/plugins/hashes.json）"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        p = Path(meipass) / "data" / "plugins" / "hashes.json"
        return p if p.exists() else None
    return None


def load_whitelist(whitelist_path) -> "dict | None":
    """加载并验证白名单表；缺失/签名无效返回 None

    优先外部 data/plugins/hashes.json，缺失时回退打包内置白名单。
    """
    import json
    candidates = []
    if whitelist_path:
        candidates.append(Path(whitelist_path))
    bundled = _bundled_whitelist_path()
    if bundled:
        candidates.append(bundled)
    for cand in candidates:
        try:
            if not cand.exists():
                continue
            data = json.loads(cand.read_text(encoding="utf-8"))
            plugins = data.get("plugins", {})
            if not isinstance(plugins, dict):
                continue
            body = json.dumps(plugins, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if verify_sig(body, data.get("sig", "")):
                return plugins
        except Exception:
            continue
    return None


def verify_plugin_file(plugin_id: str, tools_path, whitelist_path) -> tuple:
    """校验插件 tools.py 是否与白名单匹配

    返回 (ok: bool, reason: str)
    - ok=False, reason="whitelist_invalid" : 白名单缺失或签名无效 → 拒绝
    - ok=True,  reason="not_in_whitelist"  : 白名单外（远程/用户自装）→ 放行
    - ok=True,  reason="ok"                : 匹配
    - ok=False, reason="tampered"          : SHA-256 不匹配 → 拒绝
    """
    whitelist = load_whitelist(whitelist_path)
    if whitelist is None:
        return False, "whitelist_invalid"
    if plugin_id not in whitelist:
        return True, "not_in_whitelist"
    try:
        digest = hashlib.sha256(Path(tools_path).read_bytes()).hexdigest()
    except Exception as e:
        return False, f"read_failed: {e}"
    if digest == whitelist[plugin_id]:
        return True, "ok"
    return False, "tampered"


def verify_and_load(plugin_id: str, pkg_dir: str, whitelist_path: str):
    """校验通过后加载插件工具模块；未通过抛异常

    加载逻辑与 PluginManager._load_plugin 原实现一致（在守卫内完成加载，
    防止调用方绕过校验直接 exec）。
    """
    tools_path = Path(pkg_dir) / "tools.py"
    if not tools_path.exists():
        raise ImportError(f"插件 {plugin_id} 无 tools.py")

    ok, reason = verify_plugin_file(plugin_id, tools_path, whitelist_path)
    if not ok:
        if reason == "tampered":
            raise PermissionError(
                f"插件 {plugin_id} 的 tools.py 与官方白名单不符（可能被篡改），已拒绝加载")
        raise PermissionError(
            f"插件 {plugin_id} 无法通过完整性校验（{reason}），已拒绝加载")

    module_name = f"plugin_{plugin_id}"
    if module_name in sys.modules:
        del sys.modules[module_name]
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

    spec = importlib.util.spec_from_file_location(module_name, str(tools_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {tools_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
