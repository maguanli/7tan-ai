# -*- coding: utf-8 -*-
"""继续替换：跳过被锁定的文件，报告状态"""
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(r"D:\7tan\7tanAI")
NEW = ROOT / "tools" / "_tmp_authbuild" / "auth_client.pyd"

print("== 当前 python/main 进程 ==")
r = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|7tan' } | Select-Object ProcessId,Name,CommandLine | Format-List"],
    capture_output=True, text=True, timeout=60,
)
print(r.stdout[:3000] if r.stdout else r.stderr[:1000])

print("\n== 替换（跳过锁定）==")
targets = [
    ROOT / "src" / "security" / "auth_client.pyd",
    ROOT / "dist" / "_build" / "src" / "security" / "auth_client.pyd",
    ROOT / "dist" / "7tan-editor" / "_internal" / "src" / "security" / "auth_client.pyd",
]
backup_dir = ROOT / "backups" / "pyd_auth_fix"
backup_dir.mkdir(parents=True, exist_ok=True)
for t in targets:
    if not t.exists():
        print(f"  SKIP {t.relative_to(ROOT)} (不存在)")
        continue
    try:
        shutil.copy2(t, backup_dir / f"{t.parent.name}_{t.name}")
        shutil.copy2(NEW, t)
        print(f"  OK   替换 {t.relative_to(ROOT)} ({t.stat().st_size} B)")
    except PermissionError:
        print(f"  LOCK 被占用，跳过: {t.relative_to(ROOT)}")

# 清理错误命名的 auth_client_new.pyd
print("\n== 清理 auth_client_new.pyd ==")
for t in [
    ROOT / "src" / "security" / "auth_client_new.pyd",
    ROOT / "dist" / "_build" / "src" / "security" / "auth_client_new.pyd",
]:
    if t.exists():
        try:
            shutil.move(str(t), str(backup_dir / t.name))
            print(f"  OK   移入备份: {backup_dir / t.name}")
        except PermissionError:
            print(f"  LOCK 跳过: {t.relative_to(ROOT)}")

print("\n✅ 完成")
