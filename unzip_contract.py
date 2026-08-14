# -*- coding: utf-8 -*-
import zipfile, os, sys

src = r"D:\用户目录\下载\新建文件夹 123\contract_files.zip"
dst = r"D:\用户目录\下载\新建文件夹 123\contract_files"

try:
    z = zipfile.ZipFile(src)
    print("=== ZIP 内容 ===")
    for n in z.namelist():
        info = z.getinfo(n)
        print(f"{info.file_size:>10}  {n}")
    os.makedirs(dst, exist_ok=True)
    z.extractall(dst)
    print("=== 解压完成 ===")
except Exception as e:
    print("ERROR:", e)
    sys.exit(1)
