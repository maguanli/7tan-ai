# -*- coding: utf-8 -*-
"""采样发表按钮区域颜色分布"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image
from collections import Counter

def main():
    img = Image.open('data/screenshots/full_bottom.png').convert('RGB')
    # 重新截图最新状态
    import mss, ctypes, time
    user32 = ctypes.windll.user32
    user32.ShowWindow(132302, 9)
    time.sleep(0.3)
    user32.SetForegroundWindow(132302)
    time.sleep(1.0)
    with mss.mss() as sct:
        im2 = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', im2.size, im2.rgb)
        img.save('data/screenshots/full_latest.png')
    # 发表按钮区域 (980, 905)-(1100, 955)
    counter = Counter()
    for y in range(905, 955):
        for x in range(980, 1100):
            r, g, b = img.getpixel((x, y))
            counter[(r//32*32, g//32*32, b//32*32)] += 1
    print('===== 发表按钮区域颜色 (980,905)-(1100,955) =====')
    for color, cnt in counter.most_common(10):
        print(f'RGB~{color} count={cnt}')
    # 预览按钮区域对比 (880,905)-(950,955)
    counter2 = Counter()
    for y in range(905, 955):
        for x in range(880, 950):
            r, g, b = img.getpixel((x, y))
            counter2[(r//32*32, g//32*32, b//32*32)] += 1
    print('===== 预览按钮区域颜色 (880,905)-(950,955) =====')
    for color, cnt in counter2.most_common(10):
        print(f'RGB~{color} count={cnt}')

if __name__ == '__main__':
    main()
