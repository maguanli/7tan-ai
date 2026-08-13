# -*- coding: utf-8 -*-
import os, shutil, json, hashlib, subprocess, sys, datetime, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.getcwd()
HASHES = os.path.join(ROOT, "data", "plugins", "hashes.json")

# 1) 备份
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = HASHES + f".bak_manual_{ts}"
shutil.copy2(HASHES, bak)
print("✅ 备份:", bak)

# 2) 记录 novel_writer 当前 hash
h = hashlib.sha256(open(os.path.join(ROOT, "data", "plugins", "novel_writer", "tools.py"), "rb").read()).hexdigest()
print("novel_writer current sha256:", h)

# 3) 运行官方签名工具
r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "gen_plugin_hashes.py")],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("--- gen_plugin_hashes.py stdout ---")
print(r.stdout[-3000:] if r.stdout else "")
print("--- stderr ---")
print(r.stderr[-2000:] if r.stderr else "")

# 4) 验证新白名单
if os.path.exists(HASHES):
    d = json.load(open(HASHES, encoding="utf-8"))
    print("--- verify ---")
    print("novel_writer in new whitelist:", "novel_writer" in d.get("plugins", {}))
    print("new novel_writer hash:", d["plugins"].get("novel_writer"))
    print("matches current file:", d["plugins"].get("novel_writer") == h)
    # 用 pyd 的 verify_sig 自检签名
    try:
        sys.path.insert(0, ROOT)
        from src.security.plugin_guard import verify_sig
        body = json.dumps(d["plugins"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        print("sig valid:", verify_sig(body, d["sig"]))
    except Exception as e:
        print("sig check error:", e)
