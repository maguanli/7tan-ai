# -*- coding: utf-8 -*-
"""P0+P1+P2 全量验证 v2：pyd 导入 / 关键API / 安全残留检查（修正版）"""
import sys, os, importlib, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"D:\7tan\7tanAI"
sys.path.insert(0, ROOT)  # src 作为包

PASS = 0; FAIL = 0
def chk(name, ok, detail=""):
    global PASS, FAIL
    if ok: PASS += 1; print(f"  ✅ {name} {detail}")
    else:  FAIL += 1; print(f"  ❌ {name} {detail}")

print("=" * 60)
print(" [1] 13 个安全 pyd 导入测试（src 包方式）")
print("=" * 60)
mods = [
    "src.security.auth_client", "src.security.device_fingerprint",
    "src.security.entry_auth", "src.security.integrity",
    "src.security.license_verify", "src.security.rsa_verify",
    "src.security.safe_modify", "src.security.sec_config",
    "src.security.strings", "src.security.token_store",
    "src.security.trial_store", "src.core.updater", "src.agent.prompts",
]
for m in mods:
    try:
        importlib.import_module(m)
        chk(f"import {m}", True)
    except Exception as e:
        chk(f"import {m}", False, f"{type(e).__name__}: {e}")

print("=" * 60)
print(" [2] 关键 API 存在性（P1/P2 核心，按实际模块归属）")
print("=" * 60)
import src.security.auth_client as ac
import src.security.sec_config as sc
import src.security.entry_auth as ea
import src.core.updater as up
import src.security.device_fingerprint as df
api_checks = [
    ("auth_client.login",                   hasattr(ac, "login")),
    ("auth_client.refresh_token",           hasattr(ac, "refresh_token")),
    ("auth_client._collect_device_info",    hasattr(ac, "_collect_device_info")),
    ("sec_config.get_pinned_session",       hasattr(sc, "get_pinned_session")),     # TLS pin 会话
    ("sec_config.get_tls_pins",             hasattr(sc, "get_tls_pins")),           # pin 表
    ("sec_config.PinnedAdapter",            hasattr(sc, "PinnedAdapter")),          # 校验器
    ("sec_config.get_encryption_seed",      hasattr(sc, "get_encryption_seed")),   # P1-6b
    ("sec_config.verify_update_signature",  hasattr(sc, "verify_update_signature")),# P0-4
    ("entry_auth.perform_login_gate",       hasattr(ea, "perform_login_gate")),     # P2-8
    ("updater.endpoint",                    hasattr(up, "endpoint")),
    ("updater._verify_rsa_signature",       hasattr(up, "_verify_rsa_signature")), # P0-4 编译内
    ("device_fingerprint.collect_fingerprint", hasattr(df, "collect_fingerprint")),
    ("device_fingerprint.on_login",         hasattr(df, "on_login")),
]
for name, ok in api_checks:
    chk(name, ok)

print("=" * 60)
print(" [3] 运行时行为（真实执行）")
print("=" * 60)
# 3a. 设备指纹采集（P1-5）
try:
    info = ac._collect_device_info()
    ok = isinstance(info, dict) and len(info) >= 3 and info.get("device_id")
    chk("_collect_device_info() 返回完整指纹", ok,
        f"keys={list(info.keys()) if info else 'EMPTY'}" + (f", device_id={str(info['device_id'])[:12]}..." if ok else ""))
except Exception as e:
    chk("_collect_device_info() 返回完整指纹", False, f"{e}")

# 3b. 加密种子（P1-6b）
try:
    seed1 = sc.get_encryption_seed()
    seed2 = sc.get_encryption_seed()
    chk("get_encryption_seed() 稳定复现", bool(seed1) and seed1 == seed2, f"len={len(seed1)}")
except Exception as e:
    chk("get_encryption_seed() 稳定复现", False, f"{e}")

# 3c. TLS pin 表（P2-10）
try:
    pins = sc.get_tls_pins()
    chk("get_tls_pins() 返回 pin 表", isinstance(pins, (list, dict)) and bool(pins),
        f"entries={len(pins) if pins else 0}")
except Exception as e:
    chk("get_tls_pins() 返回 pin 表", False, f"{e}")

# 3d. 更新端点（加密容器读取）
try:
    ep = up.endpoint()
    chk("updater.endpoint() 读取加密端点", bool(ep) and ep.startswith("https"), ep)
except Exception as e:
    chk("updater.endpoint() 读取加密端点", False, f"{e}")

print("=" * 60)
print(" [4] 安全残留检查（_source_backup / __pycache__ / 明文py）")
print("=" * 60)
for p in [
    r"src\security\_source_backup",
    r"src\security\__pycache__",
    r"src\security\auth_client.py",
    r"src\security\sec_config.py",
    r"src\security\license_verify.py",
    r"src\security\rsa_verify.py",
    r"src\security\safe_modify.py",
    r"src\core\updater.py",
    r"src\agent\prompts.py",
    r"src\security\entry_auth.py",
]:
    chk(f"不存在: {p}", not os.path.exists(p))

print("=" * 60)
print(f" 结果: PASS={PASS}  FAIL={FAIL}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
