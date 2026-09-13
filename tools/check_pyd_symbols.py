# -*- coding: utf-8 -*-
"""检查 pyd 文件导出的 PyInit_ 符号，判断文件名与模块名是否匹配"""
import re
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

ROOT = Path(r"D:\7tan\7tanAI")

targets = [
    ROOT / "src" / "security" / "auth_client.pyd",
    ROOT / "src" / "security" / "auth_client_new.pyd",
    ROOT / "src" / "security" / "entry_auth.pyd",
    ROOT / "src" / "security" / "sec_config.pyd",
    ROOT / "src" / "security" / "device_fingerprint.pyd",
    ROOT / "src" / "security" / "integrity.pyd",
    ROOT / "src" / "security" / "license_verify.pyd",
    ROOT / "src" / "security" / "rsa_verify.pyd",
    ROOT / "src" / "security" / "safe_modify.pyd",
    ROOT / "src" / "security" / "strings.pyd",
    ROOT / "src" / "security" / "token_store.pyd",
    ROOT / "src" / "security" / "trial_store.pyd",
    ROOT / "src" / "core" / "updater.pyd",
    ROOT / "src" / "agent" / "prompts.pyd",
]

print("=" * 70)
print("pyd 文件名  vs  实际导出符号")
print("=" * 70)
for p in targets:
    if not p.exists():
        print(f"{p.name:28s} !! 文件不存在")
        continue
    b = p.read_bytes()
    syms = sorted(set(re.findall(rb"PyInit_[A-Za-z0-9_]+", b)))
    expect = "PyInit_" + p.stem
    status = "OK" if (f"PyInit_{p.stem}".encode() in syms) else "!! 不匹配!"
    print(f"{p.name:28s} {status}  导出: {[s.decode() for s in syms][:4]}")

print()
print("=" * 70)
print("dist\\_build 关键文件检查")
print("=" * 70)
checks = [
    ROOT / "dist" / "_build" / "main.py",
    ROOT / "dist" / "_build" / "build.spec",
    ROOT / "dist" / "_build" / "src" / "config" / "build_info.py",
    ROOT / "dist" / "_python" / "python.exe",
    ROOT / "dist" / "_python" / "Scripts" / "pyinstaller.exe",
    ROOT / "dist" / "_build" / "src" / "security" / "auth_client.pyd",
]
for c in checks:
    print(f"{'OK' if c.exists() else '!!'} {c.relative_to(ROOT)}  ({c.stat().st_size if c.exists() else '-'} B)")

print()
print("=" * 70)
print("dist\\_build\\src\\security 内容")
print("=" * 70)
sd = ROOT / "dist" / "_build" / "src" / "security"
if sd.exists():
    for f in sorted(sd.iterdir()):
        print(f"  {f.name} ({f.stat().st_size} B)")
else:
    print("  !! 目录不存在")
