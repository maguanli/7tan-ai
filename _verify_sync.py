# -*- coding: utf-8 -*-
import hashlib, os

DEV = r"D:\7tan\7tanAI"
BUILD = r"D:\7tan\7tanAI\dist\_build"

def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()

checks = [
    ("src/agent/model_manager.py", DEV, BUILD),
    ("src/ui/welcome_wizard.py", DEV, BUILD),
    ("src/web/routes/api_settings.py", DEV, BUILD),
    ("src/tools/monitor_tools.py", DEV, BUILD),
    ("src/tools/browser_bridge.py", DEV, BUILD),
    ("main.py", DEV, BUILD),
    ("build.spec", DEV, BUILD),
    ("requirements.txt", DEV, BUILD),
]
all_ok = True
for rel, d1, d2 in checks:
    p1, p2 = os.path.join(d1, rel), os.path.join(d2, rel)
    ok = os.path.exists(p1) and os.path.exists(p2) and md5(p1) == md5(p2)
    if not ok:
        all_ok = False
    print(f"{'OK' if ok else 'DIFF'}  {rel}")

# 检查 security 目录 pyd 完整性
sec = os.path.join(BUILD, "src", "security")
pyds = [f for f in os.listdir(sec) if f.endswith(".pyd")]
print(f"\n_build/src/security .pyd: {len(pyds)} 个 -> {sorted(pyds)}")
print("\n=== 总体: " + ("全部同步一致 ✅" if all_ok else "仍有差异 ❌") + " ===")
