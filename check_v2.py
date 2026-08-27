# -*- coding: utf-8 -*-
"""验证v2视频：文件信息 + 右下角抽帧放大"""
import os, subprocess
from PIL import Image

p = 'downloads/video_test/ch01/ch01_open_10s_v2.mp4'
if not os.path.exists(p):
    print('V2 NOT FOUND - ffmpeg may have failed')
else:
    print(f'v2 size: {os.path.getsize(p):,} bytes')

# 探测分辨率时长
r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height,duration', '-of', 'csv=p=0', p],
                   capture_output=True, text=True)
print('probe:', r.stdout.strip())

# 抽 1s/5s/9s 三帧，右下角放大（检查裁剪后是否干净）
for n in ['1', '5', '9']:
    subprocess.run(['ffmpeg', '-y', '-ss', n, '-i', p, '-frames:v', '1',
                    f'downloads/video_test/ch01/v2_f{n}.png'], capture_output=True)
    im = Image.open(f'downloads/video_test/ch01/v2_f{n}.png')
    w, h = im.size
    crop = im.crop((w-400, h-260, w, h)).resize((1200, 780), Image.NEAREST)
    crop.save(f'downloads/video_test/ch01/v2_zoom_f{n}.png')
print('DONE')
