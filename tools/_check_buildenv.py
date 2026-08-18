# -*- coding: utf-8 -*-
import sys, shutil, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

ROOT = Path(r"D:\7tan\7tanAI")
py = ROOT / ".venv" / "Scripts" / "python.exe"

print("== 编译环境检查 ==")
print(f"python: {py}  {'OK' if py.exists() else 'MISS'}")

# gcc
gcc = shutil.which("gcc")
print(f"gcc: {gcc or 'MISS'}")

# cython 版本
r = subprocess.run([str(py), "-m", "cython", "--version"], capture_output=True, text=True)
print(f"cython: {r.stdout.strip() or r.stderr.strip()}")

# 源码检查：auth_client_src.py 关键标志
src = ROOT / "tools" / "security_src" / "auth_client_src.py"
if src.exists():
    b = src.read_text(encoding="utf-8")
    flags = {
        "P1-5 device 逻辑": "device_id" in b,
        "online_verify 修复": "get(\"success\")" not in b and ("valid" in b or "ok" in b),
        "TLS pin (get_pinned_session)": "get_pinned_session" in b,
        "_collect_device_info": "_collect_device_info" in b,
        "api_publish_resource 完整": "def api_publish_resource" in b,
        "trial_call 完整": "def trial_call" in b,
    }
    for k, v in flags.items():
        print(f"  {'OK ' if v else 'MISS'} {k}")
    print(f"  行数: {len(b.splitlines())}")
else:
    print("  MISS auth_client_src.py")
