# -*- coding: utf-8 -*-
"""从 zip 提取疑点上下文（只读检查）"""
import zipfile, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ZIP = r"D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.16.zip"
zf = zipfile.ZipFile(ZIP)
names = zf.namelist()

# 1) welcome_wizard.py 中 sk- 上下文
for n in names:
    if n.endswith("welcome_wizard.py"):
        text = zf.read(n).decode("utf-8", errors="replace")
        for m in re.finditer(r"sk-[A-Za-z0-9]{8,}", text):
            s = max(0, m.start()-100); e = min(len(text), m.end()+100)
            print("###", n)
            print(text[s:e].replace("\n", " | "))
            print("---")
        break

# 2) hashes.json 中手机号上下文
for n in names:
    if n.endswith("hashes.json"):
        raw = zf.read(n)
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            continue
        for m in re.finditer(r"1[3-9]\d{9}", text):
            s = max(0, m.start()-80); e = min(len(text), m.end()+80)
            print("###", n)
            print(text[s:e].replace("\n", " | "))
            print("---")
        break

# 3) 说明书 .md 中 img.7tan.cn 上下文
for n in names:
    if n.endswith("7Tan使用说明书.md"):
        text = zf.read(n).decode("utf-8", errors="replace")
        for m in re.finditer(r"img\.7tan\.cn", text):
            s = max(0, m.start()-120); e = min(len(text), m.end()+120)
            print("###", n)
            print(text[s:e].replace("\n", " | "))
            print("---")
zf.close()
print("DONE")
