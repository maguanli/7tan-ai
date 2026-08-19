# -*- coding: utf-8 -*-
"""从 git 备份目录恢复被 filter-repo 从工作区删除的关键文件（不重新入库）"""
import os
import subprocess
import sys

BACKUP_GIT = r"D:\7tan\backups\git_bak_20260813_clean"
COMMIT = "bd4b272927e60f8890b4a9185768ac2a8aa7b8a4"
WORKDIR = r"D:\7tan\7tanAI"

FILES = [
    "data/.encryption_key",
    "data/.encryption_salt",
    "data/memory/config.json",
    "data/memory/games.json",
    "data/memory/skills.json",
    "data/users/1160130875fda0812c99c5e3.json",
    "data/users/46b9079f0394eccf3a1cd873.json",
    "data/users/4af6d680934234f361c9da11.json",
    "data/users/657d0a759eab0bb5ef899b6b.json",
    "data/users/94419b99b12c11133a4dfecc.json",
]

ok, fail = 0, 0
for rel in FILES:
    target = os.path.join(WORKDIR, rel)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    try:
        r = subprocess.run(
            ["git", "--git-dir=" + BACKUP_GIT, "show", f"{COMMIT}:{rel}"],
            capture_output=True, timeout=60,
        )
        if r.returncode != 0:
            print(f"SKIP {rel}: {r.stderr.decode('utf-8','ignore').strip()[:120]}")
            fail += 1
            continue
        with open(target, "wb") as f:
            f.write(r.stdout)
        size = os.path.getsize(target)
        print(f"RESTORED {rel} ({size} bytes)")
        ok += 1
    except Exception as e:
        print(f"ERROR {rel}: {e}")
        fail += 1

print(f"--- DONE ok={ok} fail={fail} ---")
sys.exit(0 if fail == 0 else 1)
