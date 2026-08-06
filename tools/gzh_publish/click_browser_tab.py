# -*- coding: utf-8 -*-
"""点击'浏览器'标签(338,49)，等待，截屏验证"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, time
import mss
from PIL import Image

def main():
    pyautogui.click(338, 49)
    time.sleep(2.0)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_switch_tab.png')
        print('saved after_switch_tab.png', img.size)
    print('done')

if __name__ == '__main__':
    main()
