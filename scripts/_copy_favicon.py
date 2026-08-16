# -*- coding: utf-8 -*-
"""复制 7Tan LOGO 到 WEB 静态目录作为 favicon"""
import shutil, os

src_ico = r'D:\7tan\7tanAI\data\logo\app.ico'
src_png = r'D:\7tan\7tanAI\data\logo\logo_v4_256.png'
dst_ico = r'D:\7tan\7tanAI\src\web\static\favicon.ico'
dst_png = r'D:\7tan\7tanAI\src\web\static\favicon.png'

for s, d in [(src_ico, dst_ico), (src_png, dst_png)]:
    if os.path.exists(s):
        shutil.copyfile(s, d)
        print('已复制:', s, '->', d, os.path.getsize(d), 'bytes')
    else:
        print('源文件不存在:', s)
