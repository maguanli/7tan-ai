# -*- coding: utf-8 -*-
import zipfile

zip_path = r"D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.12.zip"
zf = zipfile.ZipFile(zip_path)
names = zf.namelist()

print("=== 顶层根目录文件（非目录）===")
for n in sorted(names):
    if n.count('/') == 0:
        print(" ", n)

print("\n=== 含 web_main / start_web / 启动 的所有条目 ===")
for n in sorted(names):
    low = n.lower()
    if 'web_main' in low or 'start_web' in low or '启动' in n or 'web_service' in low:
        print(" ", n)

print("\n=== 启动网页版服务(Windows).bat 内容 ===")
found = False
for n in names:
    if '启动网页版服务' in n:
        data = zf.read(n).decode('utf-8', errors='replace')
        print("----", n, "----")
        print(data)
        found = True
        break
if not found:
    print("未找到启动网页版服务(Windows).bat")

print("\n=== README.txt 前 1500 字 ===")
for n in names:
    if n.lower() == 'readme.txt' or n.lower().endswith('/readme.txt'):
        if n.count('/') == 0:
            print(zf.read(n).decode('utf-8', errors='replace')[:1500])
            break
