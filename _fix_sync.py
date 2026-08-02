# -*- coding: utf-8 -*-
"""一次性修复脚本：pyd 替换 + 源码同步到 dist/_build"""
import shutil, os, sys

ROOT = r"D:\7tan\7tanAI"
SRC = os.path.join(ROOT, "src")
DST = os.path.join(ROOT, "dist", "_build", "src")

def log(msg):
    print(msg, flush=True)

# 1. 替换 auth_client.pyd (online_verify 修复版)
old = os.path.join(SRC, "security", "auth_client.pyd")
new = os.path.join(SRC, "security", "auth_client_new.pyd")
backup = os.path.join(ROOT, "backups", "auth_client_p1v5.bak.pyd")
if os.path.exists(old):
    os.makedirs(os.path.dirname(backup), exist_ok=True)
    shutil.copy2(old, backup)
    log(f"[1] 备份旧版 -> {backup}")
shutil.copy2(new, old)
log(f"[1] auth_client.pyd 已替换, 大小={os.path.getsize(old)} (应为262151)")

# 2. 同步 src -> dist/_build/src
ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache", "_source_backup", "*.pyc")
if os.path.exists(DST):
    shutil.rmtree(DST, ignore_errors=True)
shutil.copytree(SRC, DST, ignore=ignore, dirs_exist_ok=True)
log("[2] src 已同步到 dist/_build/src")

# 3. 同步 main.py / config / data / build.spec / requirements.txt
for f in ["main.py", "build.spec", "requirements.txt"]:
    shutil.copy2(os.path.join(ROOT, f), os.path.join(ROOT, "dist", "_build", f))
    log(f"[3] {f} 已同步")
for d in ["config", "data"]:
    sd = os.path.join(ROOT, d)
    dd = os.path.join(ROOT, "dist", "_build", d)
    if os.path.exists(dd):
        shutil.rmtree(dd, ignore_errors=True)
    shutil.copytree(sd, dd, ignore=ignore, dirs_exist_ok=True)
    log(f"[3] {d} 已同步")

# 4. 验证
app_py = os.path.join(DST, "ui", "app.py")
lg_py = os.path.join(DST, "ui", "login_dialog.py")
bs = os.path.join(ROOT, "dist", "_build", "build.spec")
checks = {
    "app.py 含 25px": "setFixedSize(25, 25)" in open(app_py, encoding="utf-8", errors="ignore").read(),
    "login_dialog 含 _chk_agree": "_chk_agree" in open(lg_py, encoding="utf-8", errors="ignore").read(),
    "login_dialog 含 ::indicator": "::indicator" in open(lg_py, encoding="utf-8", errors="ignore").read(),
    "build.spec 含 login_dialog": "src.ui.login_dialog" in open(bs, encoding="utf-8", errors="ignore").read(),
    "_build security pyd 存在": os.path.exists(os.path.join(DST, "security", "auth_client.pyd")),
}
ok = True
for k, v in checks.items():
    log(f"[4] {k}: {'✅' if v else '❌ FAIL'}")
    ok = ok and v
log("RESULT: " + ("ALL_OK" if ok else "HAS_FAIL"))
