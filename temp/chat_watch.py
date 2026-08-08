# -*- coding: utf-8 -*-
"""聊天区变化监控：定时截图对比，检测到新消息变化立即退出并报告
用法: python chat_watch.py [interval] [timeout]
"""
import sys, time, os
from PIL import Image, ImageChops
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'desktop_bot'))
from desktop_do import _grab_screen

INTERVAL = float(sys.argv[1]) if len(sys.argv) > 1 else 15   # 每15秒检测一次
TIMEOUT = float(sys.argv[2]) if len(sys.argv) > 2 else 240   # 最长监控4分钟
REGION = '860,140,400,690'  # 微信聊天区（右侧消息区）
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'temp')

def diff_ratio(a, b):
    """两图差异像素占比"""
    w, h = a.size
    # 缩小对比，提速
    sa = a.resize((w // 4, h // 4))
    sb = b.resize((w // 4, h // 4))
    diff = ImageChops.difference(sa.convert('RGB'), sb.convert('RGB'))
    # 计算差异像素数（任一通道差>20）
    import numpy as np
    arr = np.asarray(diff)
    changed = (arr.max(axis=2) > 20).sum()
    total = arr.shape[0] * arr.shape[1]
    return changed / total

def diff_bbox(a, b):
    """差异区域 bbox（原图坐标）"""
    w, h = a.size
    sa = a.resize((w // 4, h // 4))
    sb = b.resize((w // 4, h // 4))
    diff = ImageChops.difference(sa.convert('RGB'), sb.convert('RGB'))
    import numpy as np
    arr = np.asarray(diff)
    mask = (arr.max(axis=2) > 20)
    if not mask.any():
        return None
    ys, xs = np.where(mask)
    # 缩放回原图
    return (int(xs.min() * 4), int(ys.min() * 4), int(xs.max() * 4), int(ys.max() * 4))

print(f'📡 开始监控聊天区 {REGION}，每 {INTERVAL}s 检测一次，最长 {TIMEOUT}s')
prev = None
t0 = time.time()
frame = 0
while time.time() - t0 < TIMEOUT:
    img, rect = _grab_screen(REGION)
    frame += 1
    if prev is not None:
        ratio = diff_ratio(prev, img)
        if ratio > 0.01:  # 1% 像素变化即认为有新内容
            bbox = diff_bbox(prev, img)
            ts = time.strftime('%H:%M:%S')
            print(f'✅ [{ts}] 检测到画面变化! 差异像素占比={ratio:.2%}, 差异区域(相对region)={bbox}')
            img.save(os.path.join(OUT, 'chat_changed.png'))
            # 保存变化区域放大图
            if bbox:
                crop = img.crop(bbox)
                crop.save(os.path.join(OUT, 'chat_change_crop.png'))
            print('CHANGED')
            sys.exit(0)
    prev = img
    if frame == 1:
        print(f'  [基准帧已保存] {time.strftime("%H:%M:%S")}')
    else:
        print(f'  [{time.strftime("%H:%M:%S")}] 第{frame}帧 无变化')
    time.sleep(INTERVAL)
print('NO_CHANGE 监控超时，聊天区无变化')
