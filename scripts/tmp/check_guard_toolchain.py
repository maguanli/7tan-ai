# -*- coding: utf-8 -*-
import os

print("=== src/security ===")
sd = r"src/security"
print("exists:", os.path.isdir(sd))
if os.path.isdir(sd):
    print(os.listdir(sd))

print()
print("=== tools/gen_plugin_guard.py 头部 ===")
gp = r"tools/gen_plugin_guard.py"
if os.path.exists(gp):
    txt = open(gp, encoding="utf-8", errors="replace").read()
    print(txt[:3000])
else:
    print("NOT FOUND")

print()
print("=== 搜索含密钥/注入字样的文件 ===")
for root, dirs, files in os.walk(r"tools"):
    for f in files:
        if f.endswith(".py"):
            fp = os.path.join(root, f)
            try:
                t = open(fp, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if "_HMAC_ENC" in t or "hmac_key" in t or "AESGCM" in t:
                print("KEY FILE:", fp)
