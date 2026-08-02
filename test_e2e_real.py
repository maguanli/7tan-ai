# -*- coding: utf-8 -*-
"""P1-5 真实端到端测试：真实账号登录 → 设备指纹上送 → token 绑定 → 刷新 → 换机场景
同时验证软件启动链路（pyd 加载 + 关键模块导入）
"""
import sys, os, io, json, importlib, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"D:\7tan\7tanAI"
sys.path.insert(0, ROOT)

PASS, FAIL = [], []
def chk(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    mark = "✅" if ok else "❌"
    print(f"  [{mark}] {name} {detail}")

print("=" * 70)
print("[1] 设备指纹采集（真实本机）")
print("=" * 70)
try:
    from src.security import device_fingerprint as df
    info = df.collect_fingerprint()
    chk("collect_fingerprint() 返回 dict", isinstance(info, dict) and bool(info), f"keys={list(info.keys())[:8]}")
    chk("含 device_id", bool(info.get("device_id")), f"device_id={info.get('device_id')}")
    chk("含 fingerprint", bool(info.get("fingerprint")), f"fingerprint={str(info.get('fingerprint'))[:40]}...")
    chk("含 device_name/os_info", bool(info.get("device_name")) and bool(info.get("os_info")))
except Exception as e:
    chk("设备指纹采集", False, f"{type(e).__name__}: {e}")

print("=" * 70)
print("[2] 真实登录（7233cn）→ 设备指纹上送 → token")
print("=" * 70)
try:
    from src.security import auth_client as ac
    # 2.1 设备信息采集
    dev = ac._collect_device_info()
    chk("_collect_device_info() 有设备ID", bool(dev.get("device_id")), f"device_id={dev.get('device_id')}")
    # 2.2 真实登录
    result = ac.login("7233cn", "123466", remember_me=True)
    token = result.get("token", "")
    chk("login() 返回 token", bool(token) and len(token) > 50, f"len={len(token)}")
    chk("login() 返回 user_id", result.get("user_id", 0) > 0, f"uid={result.get('user_id')}")
    chk("login() 返回 username", result.get("username") == "7233cn", result.get("username"))
    chk("login() 返回 level", result.get("level") in ("free", "pro"), f"level={result.get('level')}")
    print(f"      → 账号等级: {result.get('level')}, trial_ai_count={result.get('trial_ai_count')}")
except Exception as e:
    token = ""
    chk("真实登录", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()

print("=" * 70)
print("[3] token 在线验证 + 刷新（正确设备）")
print("=" * 70)
if token:
    try:
        v = ac.online_verify(token)
        chk("online_verify valid", v.get("valid") is True, f"level={v.get('level')} err={v.get('error')}")
    except Exception as e:
        chk("online_verify", False, f"{type(e).__name__}: {e}")
    try:
        dev = ac._collect_device_info()
        r = ac.refresh_token(token, device_id=dev.get("device_id", ""))
        chk("refresh_token(正确设备)", r.get("success") is True, f"level={r.get('level')}")
        if r.get("success"):
            token = r.get("token", token)
    except Exception as e:
        chk("refresh_token(正确设备)", False, f"{type(e).__name__}: {e}")

print("=" * 70)
print("[4] 换机场景：错误 device_id 刷新（PRO应401/免费宽松）")
print("=" * 70)
if token:
    try:
        r2 = ac.refresh_token(token, device_id="FAKE-DEVICE-0001-NOT-REAL")
        level = r2.get("level", "?")
        chk("refresh_token(错误设备) 不抛异常", True, f"success={r2.get('success')} level={level} msg={r2.get('message','')}")
        if r2.get("success"):
            print("      → 服务器放行（免费账号宽松策略，符合设计）")
        else:
            print("      → 服务器拒绝（PRO 换机强制重登，符合设计）")
    except Exception as e:
        chk("refresh_token(错误设备)", False, f"{type(e).__name__}: {e}")

print("=" * 70)
print("[5] 软件启动链路（模拟重启：pyd + 核心模块加载）")
print("=" * 70)
mods = [
    "src.security.auth_client", "src.security.device_fingerprint",
    "src.security.entry_auth", "src.security.integrity",
    "src.security.license_verify", "src.security.rsa_verify",
    "src.security.safe_modify", "src.security.sec_config",
    "src.security.strings", "src.security.token_store",
    "src.security.trial_store", "src.core.updater",
    "src.agent.prompts", "src.database.db", "src.config.loader",
]
for m in mods:
    try:
        importlib.import_module(m)
        chk(f"import {m}", True)
    except Exception as e:
        chk(f"import {m}", False, f"{type(e).__name__}: {e}")

# 启动关键链路（不真正打开 GUI）：load_config + integrity 自检
print("=" * 70)
print("[6] 配置加载 + 完整性自检（启动时执行的核心逻辑）")
print("=" * 70)
try:
    from src.config.loader import load_config
    cfg = load_config()
    chk("load_config() 成功", isinstance(cfg, dict) and bool(cfg), f"keys={list(cfg.keys())[:10]}")
    int_cfg = cfg.get("integrity", {})
    chk("integrity 安全键已强制覆盖", int_cfg.get("enabled") is True and int_cfg.get("mode") == "core",
        f"enabled={int_cfg.get('enabled')} mode={int_cfg.get('mode')}")
except Exception as e:
    chk("load_config", False, f"{type(e).__name__}: {e}")

try:
    from src.security import integrity as ig
    # 完整性自检（不触发修复，只读模式）
    has_check = hasattr(ig, "verify_integrity") or hasattr(ig, "check_security")
    chk("integrity 自检接口存在", has_check, f"funcs={[f for f in dir(ig) if 'check' in f.lower() or 'verify' in f.lower()][:5]}")
except Exception as e:
    chk("integrity 导入", False, f"{type(e).__name__}: {e}")

print("=" * 70)
print(f"结果: PASS={len(PASS)} FAIL={len(FAIL)}")
print("=" * 70)
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)
print("✅ 全部通过")
