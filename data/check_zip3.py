# -*- coding: utf-8 -*-
import zipfile

zip_path = r"D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.12.zip"
zf = zipfile.ZipFile(zip_path)
names = zf.namelist()

print("=== 7tan-src 下 web 相关条目 ===")
for n in sorted(names):
    if n.startswith('7tan-src/') and ('web' in n.lower() or '启动' in n or 'start' in n.lower()):
        print(" ", n)

print("\n=== 7tan-editor/_internal 下 web 相关条目 ===")
for n in sorted(names):
    if n.startswith('7tan-editor/_internal') and ('web' in n.lower()):
        print(" ", n)

print("\n=== 所有含 启动 的条目 ===")
for n in sorted(names):
    if '启动' in n:
        print(" ", n)

print("\n=== 启动网页版服务(Windows).bat 内容 ===")
for n in names:
    if '启动网页版服务' in n:
        data = zf.read(n).decode('utf-8', errors='replace')
        print("---- 文件:", n, "----")
        print(data)
        break

print("\n=== 根目录 README.txt 内容 ===")
try:
    print(zf.read('README.txt').decode('utf-8', errors='replace')[:2000])
except KeyError:
    for n in names:
        if n.lower().endswith('readme.txt'):
            print(zf.read(n).decode('utf-8', errors='replace')[:2000])
            break
