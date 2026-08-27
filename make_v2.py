# -*- coding: utf-8 -*-
"""从原版直接裁剪放大去水印区，生成v2（等比缩放零变形）
水印区 y>=1800，裁掉底部130px -> 1080x1790
等比放大到高1920: 宽=1080*1920/1790=1158 -> 居中裁回1080
"""
import subprocess

cmd = [
    'ffmpeg', '-y',
    '-i', 'downloads/video_test/ch01/ch01_open_10s.mp4',
    '-vf', 'crop=1080:1790:0:0,scale=1158:1920:flags=lanczos,crop=1080:1920:39:0',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
    'downloads/video_test/ch01/ch01_open_10s_v2.mp4'
]
r = subprocess.run(cmd, capture_output=True, text=True)
print('returncode:', r.returncode)
if r.returncode != 0:
    print(r.stderr[-1500:])
else:
    print('OK - v2 generated')
