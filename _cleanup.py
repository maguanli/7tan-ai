# -*- coding: utf-8 -*-
import os, sys, shutil, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ROOT = r"D:\7tan\7tanAI"

# 1. 删除一次性体检脚本
one_off = ["_check2.py", "_check3.py", "_check_pre_restart.py", "_check_dist_pyd.py",
           "_check_env.py", "_check_proc.py", "_check_pyd_exports.py", "_compile_auth_client.py"]
for f in one_off:
    fp = os.path.join(ROOT, f)
    if os.path.exists(fp):
        os.remove(fp)
        print("删除:", f)
    else:
        print("跳过(不存在):", f)

# 2. 保留启动测试 → tools/startup_test.py
src = os.path.join(ROOT, "_startup_test.py")
dst = os.path.join(ROOT, "tools", "startup_test.py")
if os.path.exists(src):
    shutil.move(src, dst)
    print("移动: _startup_test.py -> tools/startup_test.py")

# 3. 查看最新日志文件
logs = sorted(glob.glob(os.path.join(ROOT, "logs", "*.log")), key=os.path.getmtime, reverse=True)
if logs:
    latest = logs[0]
    print(f"\n最新日志: {os.path.basename(latest)} ({os.path.getsize(latest)}B)")
    with open(latest, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    errs = [l for l in lines if any(k in l.lower() for k in ["error", "traceback", "exception", "failed"])]
    print(f"日志总行数: {len(lines)}, 含错误关键词: {len(errs)} 行")
    for l in errs[-5:]:
        print("  |", l.strip()[:160])
else:
    print("logs 目录无 .log 文件")

# 4. .gitignore 检查
gi = os.path.join(ROOT, ".gitignore")
if os.path.exists(gi):
    content = open(gi, encoding="utf-8").read()
    print(f"\n.gitignore 存在 ({len(content)}B)")
    if "backups" not in content:
        print("  -> backups/ 未忽略")
    if "broken" not in content:
        print("  -> *.pyd.broken* 未忽略")
else:
    print("\n.gitignore 不存在")
