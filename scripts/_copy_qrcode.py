# -*- coding: utf-8 -*-
"""复制微信登录二维码到用户文件夹"""
import os, shutil

src = os.path.join('data', 'screenshots', 'wechat_login_qrcode.png')
dst = r'D:\用户目录\下载\新建文件夹 123\11\微信扫码登录二维码.png'

if not os.path.exists(src):
    print('ERROR: 源文件不存在:', src)
    raise SystemExit(1)

os.makedirs(os.path.dirname(dst), exist_ok=True)
shutil.copy2(src, dst)
print('OK 已复制到:', dst)
print('大小:', os.path.getsize(dst), 'bytes')
