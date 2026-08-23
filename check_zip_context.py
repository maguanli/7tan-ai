# -*- coding: utf-8 -*-
"""从 zip 中提取疑似敏感文件的相关上下文，确认是否真实密钥/隐私"""
import zipfile, re, os

ZIP = r"D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.13.zip"
TARGETS = [
    "7tan-src/src/ui/welcome_wizard.py",
    "7tan-src/data/plugins/hashes.json",
    "7tan-editor/_internal/src/security/token_store.pyd",
]

z = zipfile.ZipFile(ZIP)
names = z.namelist()

# 1) welcome_wizard.py 的 sk- 上下文
print("=== welcome_wizard.py 中 sk- 上下文 ===")
for n in names:
    if n.endswith("welcome_wizard.py"):
        data = z.read(n)
        text = data.decode("utf-8", errors="ignore")
        for m in re.finditer(r"sk-[A-Za-z0-9_\-\.]{6,}", text):
            s = max(0, m.start()-80)
            e = min(len(text), m.end()+80)
            print("  命中:", m.group(0))
            print("  上下文: ..." + text[s:e].replace("\n", "\\n") + "...")
            print("  ---")

# 2) hashes.json 手机号上下文
print("=== hashes.json 手机号上下文 ===")
for n in names:
    if n.endswith("hashes.json") and "plugins" in n:
        data = z.read(n)
        text = data.decode("utf-8", errors="ignore")
        for m in re.finditer(r"1[3-9]\d{9}", text):
            s = max(0, m.start()-60)
            e = min(len(text), m.end()+60)
            print("  命中:", m.group(0))
            print("  上下文: ..." + text[s:e].replace("\n", "\\n") + "...")
            print("  ---")

# 3) ocr_work 中的手机号（web 包）
print("=== ocr_work 文件列表（web包） ===")
zw = zipfile.ZipFile(r"D:\7tan\7tanAI\dist\release\7tan-web-v1.0.13.zip")
for n in zw.namelist():
    if "ocr_work" in n.lower():
        data = zw.read(n)
        text = data.decode("utf-8", errors="ignore")
        phones = re.findall(r"1[3-9]\d{9}", text)
        print(f"  {n}  手机号{len(phones)}个: {phones[:5]}")

z.close()
zw.close()
print("完成")
