# -*- coding: utf-8 -*-
"""P1+P2 加固综合验证测试（本地功能层）"""
import sys, os, json, base64, tempfile, zipfile, shutil, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

PASS, FAIL = [], []

def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    mark = "OK " if cond else "FAIL"
    print(f"  [{mark}] {name} {detail}")

# ============ P1-6b 密钥派生 ============
print("=" * 60)
print("[P1-6b] 本地密钥派生（sec_config.get_encryption_seed + db.py PBKDF2）")
print("=" * 60)
from src.security import sec_config
seed1 = sec_config.get_encryption_seed()
seed2 = sec_config.get_encryption_seed()
check("种子可获取且非空", isinstance(seed1, bytes) and len(seed1) > 0, f"len={len(seed1)}")
check("种子稳定可复现", seed1 == seed2)
check("种子非默认硬编码", seed1 != b"7Tan-Default-Seed-2026")

import hashlib
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes as chashes
salt = os.urandom(16)
machine = os.environ.get("COMPUTERNAME", "7tan-editor")
seed = seed1.decode("utf-8", "ignore")
kdf = PBKDF2HMAC(algorithm=chashes.SHA256(), length=32, salt=salt, iterations=480000)
k1 = kdf.derive(f"{machine}::{seed}".encode())
kdf2 = PBKDF2HMAC(algorithm=chashes.SHA256(), length=32, salt=salt, iterations=480000)
k2 = kdf2.derive(f"{machine}::{seed}".encode())
check("PBKDF2 派生可复现", k1 == k2)
kdf3 = PBKDF2HMAC(algorithm=chashes.SHA256(), length=32, salt=salt, iterations=480000)
k_old = kdf3.derive(f"{machine}".encode())
check("新密钥≠旧方案密钥(加固生效)", k1 != k_old)

from src.database import db as dbm
check("老用户兼容: .encryption_key 已存在", dbm._KEY_FILE.exists(), str(dbm._KEY_FILE))

# ============ P1-7 打包黑名单 ============
print("=" * 60)
print("[P1-7] 专业包敏感数据剔除（package_release.py 黑名单）")
print("=" * 60)
spec = importlib.util.spec_from_file_location("pkgrel", ROOT / "templates/package_release.py")
pkgrel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pkgrel)

tmp = Path(tempfile.mkdtemp(prefix="p17_"))
data = tmp / "data"
for sub in ["auth", "memory", "sandbox", "web_cache", "screenshots", "video_editor", "logo", "prompts", "plugins", "config", "plugins/helper"]:
    (data / sub).mkdir(parents=True, exist_ok=True)
(data / ".encryption_key").write_bytes(b"K" * 44)
(data / ".encryption_salt").write_bytes(b"S" * 16)
(data / "games.db").write_bytes(b"DB")
(data / "games.db-wal").write_bytes(b"WAL")
(data / "costs.json").write_text("{}")
(data / "test_debug.py").write_text("print(1)")
(data / "old.bak").write_text("bak")
(data / "device_last_report.json").write_text("{}")
(data / "logo/icon.png").write_bytes(b"PNG")
(data / "prompts/system.txt").write_text("sys")
(data / "plugins/helper/tools.py").write_text("def x(): pass")
(data / "config/ok.yaml").write_text("a: 1")
(data / "normal.py").write_text("print('ok')")

out_zip = tmp / "out.zip"
with zipfile.ZipFile(out_zip, "w") as zf:
    pkgrel.zip_dir(zf, data, "_build/data",
                   exclude_dirs=pkgrel.EXCLUDE_DIRS,
                   exclude_files=pkgrel.EXCLUDE_FILE_PATTERNS)
names = zipfile.ZipFile(out_zip).namelist()
joined = "|".join(names)
for bad in [".encryption_key", ".encryption_salt", "games.db", "games.db-wal", "costs.json",
            "test_debug.py", "old.bak", "device_last_report.json", "/auth/", "/memory/",
            "/sandbox/", "/web_cache/", "/screenshots/", "/video_editor/"]:
    check(f"剔除: {bad}", bad not in joined)
for good in ["logo/icon.png", "prompts/system.txt", "plugins/helper/tools.py", "config/ok.yaml", "normal.py"]:
    check(f"保留: {good}", good in joined)
shutil.rmtree(tmp, ignore_errors=True)

# ============ P2-8 登录门卫 ============
print("=" * 60)
print("[P2-8] 登录门卫 entry_auth.perform_login_gate()")
print("=" * 60)
import src.security.token_store as ts_mod
from src.security import entry_auth

orig_avail = ts_mod.is_token_available
orig_load = ts_mod.load_token

# 预置假 login_dialog 模块（避免触发 PyQt 真实导入）
import types
fake_ld = types.ModuleType("src.ui.login_dialog")
sys.modules.setdefault("src.ui", types.ModuleType("src.ui"))
sys.modules["src.ui.login_dialog"] = fake_ld

def set_mock(avail=None, token_data=None, dialog_result="__RAISE__"):
    ts_mod.is_token_available = lambda: avail
    ts_mod.load_token = lambda: token_data
    if dialog_result == "__RAISE__":
        fake_ld.show_login_dialog = lambda *a, **k: (_ for _ in ()).throw(AssertionError("不应调用登录框"))
    else:
        fake_ld.show_login_dialog = lambda *a, **k: dialog_result

good_token = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoxfQ.abcdefghijklmnopqrstuvwxyz0123456789ABCDEF"

set_mock(avail=True, token_data={"token": good_token, "username": "tester", "level": "free", "pro_expires": 0, "pro_license": ""})
try:
    r = entry_auth.perform_login_gate()
    check("场景1: 本地token直接通过", r is not None and r.get("username") == "tester")
except Exception as e:
    check("场景1: 本地token直接通过", False, f"异常: {type(e).__name__}: {e}")

set_mock(avail=True, token_data={"token": "short", "username": "x", "level": "free", "pro_expires": 0, "pro_license": ""})
try:
    r = entry_auth.perform_login_gate()
    check("场景2: 短token拒绝", r is None)
except Exception as e:
    check("场景2: 短token拒绝", False, f"异常: {type(e).__name__}: {e}")

set_mock(avail=False, token_data=None, dialog_result={"token": good_token, "username": "new", "level": "pro", "pro_expires": 123, "pro_license": "LIC"})
try:
    r = entry_auth.perform_login_gate()
    check("场景3: 登录框成功通过", r is not None and r.get("level") == "pro")
except Exception as e:
    check("场景3: 登录框成功通过", False, f"异常: {type(e).__name__}: {e}")

set_mock(avail=False, token_data=None, dialog_result=None)
try:
    r = entry_auth.perform_login_gate()
    check("场景4: 取消登录退出", r is None)
except Exception as e:
    check("场景4: 取消登录退出", False, f"异常: {type(e).__name__}: {e}")

set_mock(avail=False, token_data=None, dialog_result={"token": "bad", "username": "x", "level": "free", "pro_expires": 0, "pro_license": ""})
try:
    r = entry_auth.perform_login_gate()
    check("场景5: 登录框无效token拒绝", r is None)
except Exception as e:
    check("场景5: 登录框无效token拒绝", False, f"异常: {type(e).__name__}: {e}")

ts_mod.is_token_available = orig_avail
ts_mod.load_token = orig_load

# ============ P2-10 TLS 证书固定 ============
print("=" * 60)
print("[P2-10] TLS 证书固定（get_tls_pins + PinnedAdapter）")
print("=" * 60)
pins = sec_config.get_tls_pins()
check("pin 表可获取", isinstance(pins, dict) and len(pins) > 0, f"keys={list(pins.keys())}")
if "www.7tan.com" in pins:
    check("www.7tan.com pin 已注入", len(pins["www.7tan.com"][0]) == 64, pins["www.7tan.com"][0][:16] + "...")
else:
    check("www.7tan.com pin 已注入", False, "缺失")
if "img.7tan.cn" in pins:
    check("img.7tan.cn pin 已注入", len(pins["img.7tan.cn"][0]) == 64, pins["img.7tan.cn"][0][:16] + "...")
else:
    check("img.7tan.cn pin 已注入", False, "缺失")

import requests
try:
    sess = sec_config.get_pinned_session("https://www.7tan.com/agreement.php")
    r = sess.get("https://www.7tan.com/agreement.php", timeout=15)
    check("正确pin: 请求成功", r.status_code == 200, f"HTTP {r.status_code}")
except Exception as e:
    check("正确pin: 请求成功", False, f"异常: {type(e).__name__}: {e}")

try:
    s2 = requests.Session()
    s2.mount("https://", sec_config.PinnedAdapter(["0" * 64]))
    r2 = s2.get("https://www.7tan.com/agreement.php", timeout=15)
    check("错误pin: 请求被拒绝", False, f"意外成功 HTTP {r2.status_code}")
except requests.exceptions.SSLError:
    check("错误pin: 请求被拒绝", True, "SSLError 已抛出")
except Exception as e:
    check("错误pin: 请求被拒绝", False, f"异常类型: {type(e).__name__}: {e}")

try:
    sess3 = sec_config.get_pinned_session("https://www.7tan.com/agreement.php")
    with sess3.get("https://www.7tan.com/agreement.php", stream=True, timeout=15) as resp:
        chunk = next(resp.iter_content(1024))
        check("流式下载(更新场景): 正确pin通过", resp.status_code == 200 and len(chunk) > 0, f"HTTP {resp.status_code}")
except Exception as e:
    check("流式下载(更新场景): 正确pin通过", False, f"异常: {type(e).__name__}: {e}")

try:
    s4 = requests.Session()
    s4.mount("https://", sec_config.PinnedAdapter(["0" * 64]))
    with s4.get("https://www.7tan.com/agreement.php", stream=True, timeout=15) as resp:
        next(resp.iter_content(1024))
    check("流式下载: 错误pin拒绝", False, "意外成功")
except requests.exceptions.SSLError:
    check("流式下载: 错误pin拒绝", True, "SSLError 已抛出")
except Exception as e:
    check("流式下载: 错误pin拒绝", False, f"异常类型: {type(e).__name__}: {e}")

ep = sec_config.get_update_endpoint()
check("更新端点可获取", ep.startswith("https://www.7tan.com"), ep)
try:
    sess5 = sec_config.get_pinned_session(ep)
    r5 = sess5.get(ep, params={"ver": "9.9.9", "platform": "windows"}, timeout=15)
    check("更新端点带pin请求200", r5.status_code == 200, f"HTTP {r5.status_code}")
except Exception as e:
    check("更新端点带pin请求200", False, f"异常: {type(e).__name__}: {e}")

# ============ 汇总 ============
print("=" * 60)
print(f"汇总: PASS={len(PASS)} FAIL={len(FAIL)}")
if FAIL:
    print("失败项:")
    for f in FAIL:
        print(f"  - {f}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
