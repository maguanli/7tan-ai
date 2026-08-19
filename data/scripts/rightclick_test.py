import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
from PIL import Image, ImageChops

# 右键前截图
before = pyautogui.screenshot(region=(600, 300, 440, 480))
before.save(r"D:\7tan\7tanAI\data\screenshots\wc_before.png")
print("before saved", flush=True)

# 右键消息位置
pyautogui.rightClick(850, 570)
time.sleep(0.8)

after = pyautogui.screenshot(region=(600, 300, 440, 480))
after.save(r"D:\7tan\7tanAI\data\screenshots\wc_after.png")
print("after saved", flush=True)

# 计算差异
diff = ImageChops.difference(before.convert("RGB"), after.convert("RGB"))
bbox = diff.getbbox()
print("diff bbox:", bbox, flush=True)

if bbox:
    # 差异区域裁剪保存，方便分析
    diff.crop(bbox).save(r"D:\7tan\7tanAI\data\screenshots\wc_diff.png")
    # 统计差异像素数
    import collections
    hist = diff.histogram()
    changed = sum(hist[10:])  # 灰度>10的像素
    print("changed px:", changed, flush=True)
    print("diff region (relative to 600,300):", bbox, flush=True)
