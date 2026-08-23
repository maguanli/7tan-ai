# -*- coding: utf-8 -*-
"""
v4 拼接：concat demuxer + 重编码（修复 v3 stream-copy 导致 NAL 损坏的问题）
先输出 ASCII 文件名 output_v4.mp4，再用 Python rename 为中文名
"""
import os, subprocess

BASE = os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说')
OUT_DIR = os.path.join(BASE, 'video')
TMP_OUT = 'output_v4.mp4'
FINAL = os.path.join(OUT_DIR, '偏差_第01章_左耳上的痣_v4.mp4')

files = [f'part{i+1:02d}_v4.mp4' for i in range(12)]
missing = [f for f in files if not os.path.exists(os.path.join(OUT_DIR, f))]
if missing:
    print('缺失:', missing)
    raise SystemExit(1)

lst = os.path.join(OUT_DIR, 'filelist_v4.txt')
with open(lst, 'w', encoding='utf-8') as f:
    for fn in files:
        f.write(f"file '{fn}'\n")

# 重编码拼接（关键：-c:v libx264 重编码，不用 -c copy）
cmd = [
    'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', 'filelist_v4.txt',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
    '-c:a', 'aac', '-b:a', '192k',
    '-movflags', '+faststart',
    TMP_OUT,
]
print('运行:', ' '.join(cmd), flush=True)
r = subprocess.run(cmd, cwd=OUT_DIR, capture_output=True, text=True,
                   encoding='utf-8', errors='replace', timeout=900)
if r.returncode != 0:
    print('FAIL')
    print(r.stderr[-2000:] if r.stderr else '')
    raise SystemExit(1)

# 重命名为中文名
tmp_path = os.path.join(OUT_DIR, TMP_OUT)
if os.path.exists(tmp_path):
    if os.path.exists(FINAL):
        os.remove(FINAL)
    os.rename(tmp_path, FINAL)
    print(f'OK -> {FINAL}')
    print(f'大小: {os.path.getsize(FINAL)//1024//1024} MB')
else:
    print('ERROR: 未找到输出文件')
