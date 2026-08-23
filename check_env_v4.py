# -*- coding: utf-8 -*-
"""检查图片 + ffmpeg 版本"""
import os, subprocess

base = os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说')
img_dir = os.path.join(base, 'images')
aud_dir = os.path.join(base, 'audio')

print("=== images 目录 ===")
for f in sorted(os.listdir(img_dir)):
    p = os.path.join(img_dir, f)
    print(f"{os.path.getsize(p):>10,}  {f}")

print("\n=== audio 目录 ===")
for f in sorted(os.listdir(aud_dir)):
    p = os.path.join(aud_dir, f)
    print(f"{os.path.getsize(p):>10,}  {f}")

print("\n=== ffmpeg 版本 ===")
r = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
print(r.stdout.split('\n')[0] if r.stdout else r.stderr[:300])

print("\n=== 滤镜检查 ===")
r2 = subprocess.run(['ffmpeg', '-hide_banner', '-filters'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
filters = r2.stdout or r2.stderr
for name in ['zoompan', 'gradients', 'ass', 'subtitles', 'drawtext']:
    print(name, 'OK' if any(l.strip().startswith(name) for l in filters.splitlines()) else 'MISSING')
