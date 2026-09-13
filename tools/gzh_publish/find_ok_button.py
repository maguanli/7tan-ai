# -*- coding: utf-8 -*-
"""重新打开原创面板→扫描面板区域找绿色/蓝色按钮色块"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui
import mss
from PIL import Image

def main():
    # 1. 打开原创面板
    pyautogui.click(750, 518)
    time.sleep(1.5)
    # 2. 截屏面板区域
    with mss.mss() as sct:
        mon = sct.monitors[1]
        region = {'left': mon['left'] + 300, 'top': mon['top'] + 340, 'width': 820, 'height': 640}
        img = sct.grab(region)
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/dialog_color.png')
        print('saved', img.size)
    # 3. 扫描绿色/蓝色按钮色块
    im = Image.open('data/screenshots/dialog_color.png').convert('RGB')
    W, H = im.size
    # 微信绿 #07C160 约 (7,193,96)；蓝色 #576B95
    targets = []
    for y in range(0, H, 4):
        for x in range(0, W, 4):
            r, g, b = im.getpixel((x, y))
            # 绿色检测
            if g > 140 and r < 100 and b < 140 and g - r > 60:
                targets.append(('green', x + 300, y + 340))
            # 蓝色检测
            elif b > 120 and r < 120 and g < 140 and b - r > 40:
                targets.append(('blue', x + 300, y + 340))
    # 聚簇：按颜色和粗略位置去重
    seen = set()
    for color, x, y in targets:
        key = (color, x // 60, y // 40)
        if key not in seen:
            seen.add(key)
            print(f'{color} @ ({x},{y})')
    print('total pixels:', len(targets))

if __name__ == '__main__':
    main()
