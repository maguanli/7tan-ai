# -*- coding: utf-8 -*-
"""点击弹层群发通知蓝字，截图验证"""
import sys, io, time, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui
import mss
from PIL import Image

def main():
    user32 = ctypes.windll.user32
    user32.ShowWindow(132302, 9)
    time.sleep(0.3)
    user32.SetForegroundWindow(132302)
    time.sleep(0.8)
    pyautogui.click(488, 519)
    time.sleep(3.0)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_click_qunfa.png')
        print('saved after_click_qunfa.png')

if __name__ == '__main__':
    main()
