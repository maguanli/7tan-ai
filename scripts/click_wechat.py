# -*- coding: utf-8 -*-
"""点击任务栏微信图标并截屏验证"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
import pyautogui
import mss
from PIL import Image

x, y = 702, 699
print('clicking wechat icon at', x, y)
pyautogui.click(x, y)
time.sleep(2.5)

with mss.mss() as sct:
    monitor = sct.monitors[1]
    img = sct.grab(monitor)
    pil = Image.frombytes('RGB', img.size, img.rgb)
    out = 'data/screenshots/wechat_after_click.png'
    pil.save(out)
    print('saved:', out, pil.size)
