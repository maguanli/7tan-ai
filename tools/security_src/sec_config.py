"""
安全配置容器 — integrity 开关与敏感端点（AES-256-GCM 加密存储）
编译为 .pyd 后无法被反编译，保护完整性校验开关与服务器端点。
"""
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from requests.adapters import HTTPAdapter

_KEY_PART1 = b':\x7f,\x91\xe4\xb8U\r\xc6\xd2\x88\xfe\x17\xa3Ki'
_KEY_PART2 = b'\x8b\x1e_\xc3"\xd7\x9a@\xeea=\xb5\xf9\x04|\xa6'
_NONCE_PREFIX = b'\x7f\x4a\x2e\x91'


def _assemble_key() -> bytes:
    return _KEY_PART1 + _KEY_PART2


def _decrypt(encrypted_b64: str) -> str:
    if not encrypted_b64:
        return ""
    try:
        raw = base64.b64decode(encrypted_b64)
    except Exception:
        return ""
    if len(raw) < 12:
        return ""
    nonce = raw[:12]
    ct = raw[12:]
    try:
        return AESGCM(_assemble_key()).decrypt(nonce, ct, None).decode("utf-8")
    except Exception:
        return ""


# 加密值（构建时由 tools/gen_sec_config.py 注入）
_INTEGRITY_ENC = "'f0oukTE0B8fNAaXV4WlkA5vk/nXyLOHnxdi9U4idc13cLuaHP6L502pIlxclQynDbT0fhzf43gzKjeUWyy8kIrLdGUjomiKhQeMDy52dD/RsoIpI/ESftWJUNAzdF46PSzSgTU9x5mcolBSKQ9byEirxPlJCXwbJ9Obo51BLkda51ECUJKTvbYNGHd81xkjZq6ngEaWKjE1hvfflDQ+K82hM9scf7Sk7SYcjloo/ju3sWLXeSKwOeB0BcIpjJLjVx003vgLP7dL+6rWyX4R0uiheNiz1c/x82gNSeaPFINAmvAgQRU7TH7y3wIbi9aLN'"
_UPDATE_ENC = "'f0oukSUW2+B6r8ycDhzpK/hwUov6toA9XkGuIZ3WyluCHoXjm5UPZmaI4zn+AobtjKB0iHmJa8FwO/1Fmw/KazaCo0WD'"
_TELEMETRY_ENC = "'f0oukZ3HxKY6jNpAPo2YZZ9DIgIUp2f1NvhIRLqWQRCBY6ZsBB9XLe1ZRdca7owqEG0qZmkgtNNfgj1bKQPezAnx3VxoxSri'"
_ENC_SEED_ENC = "'f0oukUpk6+cQpk0IJXOnIC7A2Hia336HppC9nf98HkUK40/8AVRA83zu6y0ujr82X8FLdPGRZNhF/KyfNLAcLHi4M+0Qd5AR2r/EPEUv20LscyQoYccK90W3vNs='"
_TLS_PINS_ENC = "'f0oukTLS_PLACEHOLDER_REGEN_BY_GEN_SEC_CONFIG'"


def get_integrity_config() -> dict:
    """返回完整性校验的安全配置（不信任 config.yaml 明文）"""
    import json
    try:
        data = json.loads(_decrypt(_INTEGRITY_ENC) or "{}")
    except Exception:
        data = {}
    defaults = {
        "enabled": True, "mode": "core", "auto_repair": False,
        "developer_mode": False, "confirm_phrase": "我已知晓风险并信任此次修改",
        "show_status": True, "log_all_checks": True, "tamper_alert_email": "",
    }
    defaults.update({k: v for k, v in data.items() if v is not None})
    return defaults


def get_update_endpoint() -> str:
    return _decrypt(_UPDATE_ENC) or "https://www.7tan.com/api/update/check.php"


def get_telemetry_endpoint() -> str:
    return _decrypt(_TELEMETRY_ENC) or "https://www.7tan.com/api/telemetry/build.php"


def get_encryption_seed() -> bytes:
    """返回本地密钥派生种子（P1-6b：AES-256-GCM 解密，不落盘）"""
    s = _decrypt(_ENC_SEED_ENC)
    if not s:
        return b"7Tan-Default-Seed-2026"
    return s.encode("utf-8")


def get_tls_pins() -> dict:
    """返回 TLS 证书固定指纹表 {host: [sha256_spki_hex, ...]}（P2-10）"""
    import json
    try:
        data = json.loads(_decrypt(_TLS_PINS_ENC) or "{}")
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


class PinnedAdapter(HTTPAdapter):
    """校验服务端证书 SPKI 指纹是否在白名单内（TLS 证书固定）。

    继承 requests.adapters.HTTPAdapter：正常 HTTPS 链路完全不变；
    请求完成后从响应底层连接取服务端证书，SPKI 不在白名单内
    → 抛 SSLError 拒绝（调用方按网络错误处理，不使用响应内容）。
    注：requests 新版的 cert_verify 收到的是连接池对象（无 sock），
    因此在校验在 send() 完成后基于 resp.raw._connection 执行。
    """
    def __init__(self, pins, *args, **kwargs):
        from requests.adapters import HTTPAdapter
        self._pins = set(pins or [])
        super().__init__(*args, **kwargs)

    def send(self, request, *args, **kwargs):
        resp = super().send(request, *args, **kwargs)
        if not self._pins:
            return resp
        try:
            import hashlib
            import requests
            from cryptography import x509
            from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
            raw = resp.raw
            conn = getattr(raw, "_connection", None)
            sock = getattr(conn, "sock", None)
            if sock is None:
                return resp
            peer_der = sock.getpeercert(binary_form=True)
            if not peer_der:
                return resp
            cert_obj = x509.load_der_x509_certificate(peer_der)
            spki = cert_obj.public_key().public_bytes(
                Encoding.DER, PublicFormat.SubjectPublicKeyInfo
            )
            digest = hashlib.sha256(spki).hexdigest()
            if digest not in self._pins:
                raise requests.exceptions.SSLError(
                    "TLS 证书固定校验失败 (SPKI=%s...)" % digest[:16]
                )
        except requests.exceptions.SSLError:
            raise
        except Exception:
            pass
        return resp


def get_pinned_session(url: str = None):
    """创建带证书固定的 requests.Session（P2-10）。

    按 URL 的 host 查找 pin 表；无 pin 配置时回退普通 Session（不影响功能）。
    """
    import requests
    s = requests.Session()
    try:
        pins = get_tls_pins()
        host = ""
        if url and "//" in url:
            host = url.split("//", 1)[1].split("/")[0].split(":")[0]
        pin_list = pins.get(host, []) if host else []
        if pin_list:
            s.mount("https://", PinnedAdapter(pin_list))
    except Exception:
        pass
    return s


def verify_update_signature(file_path: str, sig_b64: str, public_key_pem: str = None) -> bool:
    """验证更新包 RSA 签名（SHA-256 + PKCS1v15）"""
    try:
        if public_key_pem is None:
            from .strings import get_public_key
            public_key_pem = get_public_key()
        pub = load_pem_public_key(public_key_pem.encode("ascii"))
        sig = base64.b64decode(sig_b64)
        import hashlib
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        pub.verify(sig, h.digest(), padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


def verify_update_signature_with_hash(sha256_hex: str, sig_b64: str, public_key_pem: str = None) -> bool:
    """验证更新包签名（基于预先计算的 SHA-256 摘要）"""
    try:
        if public_key_pem is None:
            from .strings import get_public_key
            public_key_pem = get_public_key()
        pub = load_pem_public_key(public_key_pem.encode("ascii"))
        sig = base64.b64decode(sig_b64)
        digest = bytes.fromhex(sha256_hex)
        pub.verify(sig, digest, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False
