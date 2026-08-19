# -*- coding: utf-8 -*-
import zipfile

zip_path = r"D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.12.zip"
zf = zipfile.ZipFile(zip_path)
names = zf.namelist()

print("=== 7tan-src 下所有条目（源码部分）===")
for n in sorted(names):
    if n.startswith('7tan-src/'):
        print(" ", n)

print("\n=== 启动网页版服务(Windows).bat 内容 ===")
try:
    info = zf.getinfo('启动网页版服务(Windows).bat')
    data = zf.read(info).decode('utf-8', errors='replace')
    print(data)
except KeyError:
    # 可能带目录前缀
    for n in names:
        if '启动网页版服务' in n:
            print("找到:", n)
            print(zf.read(n).decode('utf-8', errors='replace'))
