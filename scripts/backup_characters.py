# -*- coding: utf-8 -*-
"""备份现有江辰定妆图到 backup_old"""
import shutil, os
src = r'D:/7tan/7tanAI/镜像同事_小说/定妆图'
dst = os.path.join(src, 'backup_old')
os.makedirs(dst, exist_ok=True)
files = [f for f in os.listdir(src)
         if f.startswith('character_jiangchen') and os.path.isfile(os.path.join(src, f))]
for f in files:
    shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
print('backup done:', files)
