# -*- coding: utf-8 -*-
"""诊断 ffmpeg 打开中文目录下文件的问题"""
import os, subprocess

BASE = os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说')
IMG = os.path.join(BASE, 'images')
img = os.path.join(IMG, 'ch01_02.png')

print("1) Python 检查文件:")
print("   exists:", os.path.exists(img))
print("   size:", os.path.getsize(img) if os.path.exists(img) else None)

print("\n2) ffmpeg -i 相对路径 (cwd=BASE):")
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', 'images/ch01_02.png', '-frames:v', '1', '-f', 'null', '-'],
                   cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
print("   rc:", r.returncode)
print("   err:", (r.stderr or '')[-300:].replace('\n', ' | '))

print("\n3) ffmpeg -i 绝对路径 (cwd=BASE):")
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', img, '-frames:v', '1', '-f', 'null', '-'],
                   cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
print("   rc:", r.returncode)
print("   err:", (r.stderr or '')[-300:].replace('\n', ' | '))

print("\n4) ffmpeg -i 绝对路径 (cwd=D:\\7tan\\7tanAI):")
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', img, '-frames:v', '1', '-f', 'null', '-'],
                   cwd=r'D:\7tan\7tanAI', capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
print("   rc:", r.returncode)
print("   err:", (r.stderr or '')[-300:].replace('\n', ' | '))

print("\n5) 复制图片到无中文目录再打开:")
import shutil
tmp = os.path.join(r'D:\7tan\7tanAI', 'test_img.png')
shutil.copy2(img, tmp)
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', tmp, '-frames:v', '1', '-f', 'null', '-'],
                   cwd=r'D:\7tan\7tanAI', capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
print("   rc:", r.returncode)
print("   err:", (r.stderr or '')[-300:].replace('\n', ' | '))
os.remove(tmp)

print("\n6) ffprobe 相对路径 (cwd=BASE):")
r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', 'images/ch01_02.png'],
                   cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
print("   rc:", r.returncode, "out:", (r.stdout or r.stderr)[:100])
