# -*- coding: utf-8 -*-
"""模拟 7Tan 启动导入链测试（等价于重启时的加载过程）"""
import sys, os, traceback
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = r"D:\7tan\7tanAI"
os.chdir(ROOT)
sys.path.insert(0, ROOT)

ok_count = 0
fail_count = 0

def step(name, fn):
    global ok_count, fail_count
    try:
        fn()
        ok_count += 1
        print(f"  [OK] {name}")
    except Exception as e:
        fail_count += 1
        print(f"  [FAIL] {name}: {type(e).__name__}: {e}")
        traceback.print_exc()

print("=== 1. 版本信息 ===")
def t_version():
    from src.config.version import APP_VERSION
    print(f"       APP_VERSION = {APP_VERSION}")
    assert APP_VERSION == "1.0.6"
step("version.py", t_version)

print("\n=== 2. 关键安全模块导入（启动必经） ===")
def t_auth():
    import src.security.auth_client as ac
    assert hasattr(ac, "login"), "auth_client 缺 login"
    print(f"       auth_client OK: login={hasattr(ac,'login')}, LoginFailed={hasattr(ac,'LoginFailed')}")
step("src.security.auth_client", t_auth)

def t_entry():
    import src.security.entry_auth as ea
    print(f"       entry_auth OK: {[n for n in dir(ea) if not n.startswith('_')][:6]}")
step("src.security.entry_auth", t_entry)

def t_guard():
    import src.security.plugin_guard as pg
    print(f"       plugin_guard OK: {[n for n in dir(pg) if not n.startswith('_')][:8]}")
step("src.security.plugin_guard", t_guard)

def t_others():
    import src.security.sec_config, src.security.license_verify, src.security.rsa_verify
    import src.security.device_fingerprint, src.security.strings, src.security.safe_modify
    import src.security.token_store, src.security.trial_store, src.security.integrity
    import src.core.updater, src.agent.prompts
    print("       sec_config/license_verify/rsa_verify/device_fingerprint/strings/safe_modify/token_store/trial_store/integrity/updater/prompts 全部导入 OK")
step("其余 11 个安全模块", t_others)

print("\n=== 3. 登录对话框导入（崩溃点复测） ===")
def t_login_dialog():
    import src.ui.login_dialog as ld
    print(f"       login_dialog OK: 类={[n for n in dir(ld) if 'Login' in n][:4]}")
step("src.ui.login_dialog", t_login_dialog)

print("\n=== 4. 插件系统（白名单 + 加载入口） ===")
def t_plugin_mgr():
    import src.plugins.manager as m
    print(f"       plugins.manager OK: {[n for n in dir(m) if not n.startswith('_')][:8]}")
step("src.plugins.manager", t_plugin_mgr)

def t_hashes():
    import json
    h = json.load(open(os.path.join(ROOT, "data", "plugins", "hashes.json"), encoding="utf-8"))
    n = len(h.get("plugins", {}))
    assert n >= 39, f"白名单只有 {n} 条"
    print(f"       hashes.json: {n} 个插件哈希 + sig={h.get('sig','')[:16]}...")
step("白名单对账(≥39)", t_hashes)

print("\n=== 5. 语音插件导入 ===")
def t_tts():
    import importlib.util
    for plug in ["tts_piper", "whisper_stt"]:
        p = os.path.join(ROOT, "data", "plugins", plug, "tools.py")
        spec = importlib.util.spec_from_file_location(f"plugin_{plug}", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        print(f"       {plug} OK")
step("tts_piper + whisper_stt", t_tts)

print("\n=== 6. 语音引擎路径探测（与代码候选一致） ===")
def t_voice():
    import importlib.util, os
    p = os.path.join(ROOT, "data", "plugins", "whisper_stt", "tools.py")
    spec = importlib.util.spec_from_file_location("whisper_stt", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # 找到 WHISPER_CANDIDATES 或类似
    cands = getattr(mod, "WHISPER_CANDIDATES", None) or getattr(mod, "CANDIDATES", None)
    if cands:
        found = [c for c in cands if os.path.exists(c)]
        print(f"       whisper 候选 {len(cands)} 个, 可用 {len(found)} 个: {found}")
        assert found, "whisper 无可用引擎!"
    else:
        print("       (未找到候选常量, 跳过)")
step("whisper 引擎可用", t_voice)

print(f"\n===== 汇总: {ok_count}/{ok_count+fail_count} 通过 =====")
sys.exit(0 if fail_count == 0 else 1)
