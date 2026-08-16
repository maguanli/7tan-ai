# -*- coding: utf-8 -*-
import zipfile

zip_path = r"D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.12.zip"
zf = zipfile.ZipFile(zip_path)
names = zf.namelist()
print("总条目数:", len(names))

# 顶层结构
top = set()
for n in names:
    parts = n.split('/')
    if len(parts) >= 2 and parts[1]:
        top.add(parts[0] + '/' + parts[1] + '/')
    elif len(parts) == 1:
        top.add(parts[0])
    else:
        top.add(parts[0] + '/')

print("\n=== 顶层结构 ===")
for t in sorted(top)[:120]:
    print(" ", t)

print("\n=== WEB / 启动 相关文件 ===")
seen = set()
for n in names:
    low = n.lower()
    if any(k in low for k in ['web_main', '启动网页', '启动(', 'web/static', 'web\\static', 'web_autostart', 'start_web', '7tanweb', '.bat', '.sh', '.command', '说明书']):
        if n not in seen:
            seen.add(n)
            print(" ", n)
