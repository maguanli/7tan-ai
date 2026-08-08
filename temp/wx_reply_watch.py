# -*- coding: utf-8 -*-
"""微信回复监控 v2：PrintWindow 抓取微信窗口内容（免疫遮挡），定时对比检测新消息
用法: python wx_reply_watch.py [interval] [timeout]
"""
import sys, time, os
from PIL import Image, ImageChops
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from printwin_shot import print_window

INTERVAL = float(sys.argv[1]) if len(sys.argv) > 1 else 20   # 每20秒
TIMEOUT = float(sys.argv[2]) if len(sys.argv) > 2 else 600   # 最长10分钟
HWND_WX = 1313304
OUT = os.path.dirname(os.path.abspath(__file__))

def diff_ratio(a, b):
    w, h = a.size
    sa = a.resize((w // 4, h // 4))
    sb = b.resize((w // 4, h // 4))
    diff = ImageChops.difference(sa.convert('RGB'), sb.convert('RGB'))
    import numpy as np
    arr = np.asarray(diff)
    return (arr.max(axis=2) > 20).sum() / (arr.shape[0] * arr.shape[1])

print(f'📡 微信回复监控 v2 (PrintWindow免疫遮挡) 每{INTERVAL}s一次，最长{TIMEOUT}s')
prev = None
t0 = time.time()
frame = 0
while time.time() - t0 < TIMEOUT:
    shot = os.path.join(OUT, f'wx_frame_{frame}.png')
    try:
        print_window(HWND_WX, shot)
    except Exception as e:
        print(f'  [err] {e}')
        time.sleep(INTERVAL)
        continue
    img = Image.open(shot).convert('RGB')
    frame += 1
    if prev is not None:
        ratio = diff_ratio(prev, img)
        if ratio > 0.005:  # 0.5% 像素变化
            ts = time.strftime('%H:%M:%S')
            print(f'✅ [{ts}] 检测到画面变化! 差异={ratio:.2%}')
            # 保存变化帧
            import shutil
            shutil.copy(shot, os.path.join(OUT, 'wx_changed.png'))
            print('CHANGED')
            sys.exit(0)
    prev = img
    if frame == 1:
        print(f'  [基准帧] {time.strftime("%H:%M:%S")}')
    else:
        print(f'  [{time.strftime("%H:%M:%S")}] 第{frame}帧 无变化')
    time.sleep(INTERVAL)
print('NO_CHANGE 监控超时')
