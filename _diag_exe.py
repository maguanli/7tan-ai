# -*- coding: utf-8 -*-
"""诊断：exe 类型 + 实际运行报错"""
import os, subprocess, struct, time

exe = r"D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe"
size = os.path.getsize(exe)

# 1. 检查 exe 尾部是否有 PKG 归档（onefile 特征）
with open(exe, "rb") as f:
    f.seek(max(0, size - 65536))
    tail = f.read()

pkg_magic = b"MEI\x00\x00\x00"  # onefile PKG 特征
found = tail.find(b"MEI")
print(f"exe 大小: {size} ({size/1024/1024:.1f} MB)")
print(f"尾部含 'MEI' 标记(onefile特征): {'是 - 可能是 onefile' if found >= 0 else '否 - 疑似 onedir 引导器'}")

# 2. 检查 _internal 是否有 PYZ
internal = r"D:\7tan\7tanAI\dist\7tan-editor\_internal"
pyz = os.path.join(internal, "PYZ.pyz")
print(f"\nPYZ.pyz 存在: {os.path.exists(pyz)}")
if os.path.exists(pyz):
    print(f"PYZ.pyz 大小: {os.path.getsize(pyz)}")

# 3. 备份 exe 对比
bak = r"D:\7tan\7tanAI\dist\7tan-editor_backup_周六022608_001946.exe"
if os.path.exists(bak):
    print(f"\n备份 exe 存在: {os.path.getsize(bak)} bytes")
    with open(bak, "rb") as f:
        f.seek(max(0, os.path.getsize(bak) - 65536))
        btail = f.read()
    print(f"备份 exe 含 MEI: {btail.find(b'MEI') >= 0}")

# 4. 运行 exe 看报错（5秒超时）
print("\n=== 实际运行 exe (5s 超时) ===")
try:
    r = subprocess.run([exe], capture_output=True, timeout=5, 
                       creationflags=subprocess.CREATE_NO_WINDOW)
    print(f"退出码: {r.returncode}")
    if r.stdout:
        print("stdout:", r.stdout[:500])
    if r.stderr:
        print("stderr:", r.stderr[:500])
except subprocess.TimeoutExpired:
    print("5秒未退出 → exe 可能正常启动运行中（GUI 程序）")
except Exception as e:
    print("启动异常:", e)
