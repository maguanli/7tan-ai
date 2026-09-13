# -*- coding: utf-8 -*-
"""重新编译 auth_client.pyd — 修复 PyInit_auth_client_new 模块名不匹配问题"""
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(r"D:\7tan\7tanAI")
SRC = ROOT / "tools" / "security_src" / "auth_client_src.py"
TMP = ROOT / "tools" / "_tmp_authbuild"

print("== 1. 准备源码（文件名 = 目标模块名 auth_client）==")
TMP.mkdir(parents=True, exist_ok=True)
py_name = TMP / "auth_client.py"
shutil.copy2(SRC, py_name)
print(f"  {py_name} ({py_name.stat().st_size} B)")

print("== 2. Cython 转译 py → c ==")
r = subprocess.run(
    [sys.executable, "-m", "cython", "-3", "-o", str(TMP / "auth_client.c"), str(py_name)],
    capture_output=True, text=True, timeout=180,
)
if r.returncode != 0:
    print("  FAIL:", r.stderr[-1500:])
    sys.exit(1)
print(f"  OK auth_client.c ({ (TMP/'auth_client.c').stat().st_size } B)")

print("== 3. gcc 编译 c → pyd ==")
python_include = sysconfig.get_paths()["include"]
python_lib = os.path.join(sys.base_prefix, "libs")
pyd_out = TMP / "auth_client.pyd"
r = subprocess.run(
    ["gcc", "-shared", "-O2", "-fPIC",
     f"-I{python_include}", str(TMP / "auth_client.c"),
     "-o", str(pyd_out),
     f"-L{python_lib}", f"-lpython{sys.version_info.major}{sys.version_info.minor}"],
    capture_output=True, text=True, timeout=300,
)
if r.returncode != 0:
    print("  FAIL:", r.stderr[-1500:])
    sys.exit(1)
print(f"  OK {pyd_out.name} ({pyd_out.stat().st_size} B)")

print("== 4. 校验导出符号 ==")
import re
b = pyd_out.read_bytes()
syms = sorted(set(re.findall(rb"PyInit_[A-Za-z0-9_]+", b)))
print("  导出:", [s.decode() for s in syms])
if b"PyInit_auth_client" not in syms:
    print("  FAIL: 缺少 PyInit_auth_client")
    sys.exit(1)
print("  OK: PyInit_auth_client 导出正确")

print("== 5. 替换三处 ==")
targets = [
    ROOT / "src" / "security" / "auth_client.pyd",
    ROOT / "dist" / "_build" / "src" / "security" / "auth_client.pyd",
    ROOT / "dist" / "7tan-editor" / "_internal" / "src" / "security" / "auth_client.pyd",
]
backup_dir = ROOT / "backups" / "pyd_auth_fix"
backup_dir.mkdir(parents=True, exist_ok=True)
for t in targets:
    if t.exists():
        shutil.copy2(t, backup_dir / f"{t.parent.name}_{t.name}")
        print(f"  备份: {backup_dir / (t.parent.name + '_' + t.name)}")
    shutil.copy2(pyd_out, t)
    print(f"  替换: {t.relative_to(ROOT)} ({t.stat().st_size} B)")

print("== 6. 清理错误命名的 auth_client_new.pyd ==")
for t in [
    ROOT / "src" / "security" / "auth_client_new.pyd",
    ROOT / "dist" / "_build" / "src" / "security" / "auth_client_new.pyd",
]:
    if t.exists():
        shutil.move(str(t), str(backup_dir / t.name))
        print(f"  移入备份: {backup_dir / t.name}")

print("\n✅ 全部完成")
