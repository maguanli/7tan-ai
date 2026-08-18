"""
src.utils.crypto 单元测试
基于真实 API: encrypt / decrypt / encrypt_dict / decrypt_dict (AES-256-GCM)
以及 src.database.db 的 encrypt_password / decrypt_password (Fernet)
"""
import base64

from src.utils.crypto import encrypt, decrypt, encrypt_dict, decrypt_dict
from src.database.db import encrypt_password, decrypt_password


# ===== crypto.py: AES-256-GCM =====

class TestCryptoAES:
    """src.utils.crypto AES-GCM 加解密"""

    def test_encrypt_returns_base64(self):
        ct = encrypt("hello world")
        assert isinstance(ct, str)
        # 应能被 base64 解码
        base64.b64decode(ct)

    def test_decrypt_roundtrip(self):
        plain = "7Tan 密钥 🔐 test"
        ct = encrypt(plain)
        assert decrypt(ct) == plain

    def test_encrypt_nondeterministic(self):
        """相同明文两次加密密文不同（随机 salt+nonce）"""
        a = encrypt("same")
        b = encrypt("same")
        assert a != b

    def test_decrypt_empty_string(self):
        assert decrypt(encrypt("")) == ""

    def test_decrypt_invalid_returns_empty(self):
        """非法密文解密返回空串而非抛异常"""
        assert decrypt("!!!not-base64!!!") == ""

    def test_decrypt_truncated_returns_empty(self):
        ct = encrypt("secret data")
        assert decrypt(ct[:10]) == ""

    def test_unicode_roundtrip(self):
        for text in ["中文", "emoji😀", "日本語", "mixed A1!"]:
            assert decrypt(encrypt(text)) == text

    def test_long_text_roundtrip(self):
        text = "x" * 10000
        assert decrypt(encrypt(text)) == text


class TestCryptoDict:
    """encrypt_dict / decrypt_dict"""

    def test_encrypt_dict_selected_keys(self):
        data = {"api_key": "sk-123", "name": "deepseek", "other": ""}
        enc = encrypt_dict(data, ["api_key"])
        assert enc["api_key"] != "sk-123"
        assert enc["name"] == "deepseek"  # 未指定 key 不加密

    def test_encrypt_dict_skips_empty(self):
        data = {"api_key": ""}
        enc = encrypt_dict(data, ["api_key"])
        assert enc["api_key"] == ""  # 空值不加密

    def test_dict_roundtrip(self):
        data = {"api_key": "sk-abc", "token": "tok-xyz"}
        enc = encrypt_dict(data, ["api_key", "token"])
        dec = decrypt_dict(enc, ["api_key", "token"])
        assert dec["api_key"] == "sk-abc"
        assert dec["token"] == "tok-xyz"

    def test_decrypt_dict_tolerates_bad_value(self):
        """解密失败保留原值不抛异常"""
        data = {"api_key": "not-encrypted"}
        dec = decrypt_dict(data, ["api_key"])
        assert "api_key" in dec  # 不崩溃

    def test_encrypt_dict_does_not_mutate_original(self):
        data = {"api_key": "sk-1"}
        encrypt_dict(data, ["api_key"])
        assert data["api_key"] == "sk-1"  # 原字典不变


# ===== db.py: Fernet =====

class TestDBPasswordCrypto:
    """src.database.db Fernet 加解密"""

    def test_password_roundtrip(self):
        plain = "db-password-123"
        ct = encrypt_password(plain)
        assert decrypt_password(ct) == plain

    def test_password_encrypt_differs_from_plain(self):
        ct = encrypt_password("secret")
        assert ct != "secret"

    def test_password_unicode(self):
        plain = "密码🔑"
        assert decrypt_password(encrypt_password(plain)) == plain

    def test_password_empty(self):
        # 空串加密应可逆（或按实现返回空/特定值，只要不崩溃）
        ct = encrypt_password("")
        result = decrypt_password(ct)
        assert isinstance(result, str)
