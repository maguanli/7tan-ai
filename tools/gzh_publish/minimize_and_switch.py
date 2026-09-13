# -*- coding: utf-8 -*-
"""最小化遮挡的监控窗口(656614)→聚焦7Tan主窗口(132302)→点击浏览器标签→截图验证"""
import sys, io, time, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui
import mss
from PIL import Image
from ctypes import wintypes

user32 = ctypes.windll.user32
MONITOR_WND = 656614   # 代码修改实时监控（遮挡）
MAIN_WND = 132302      # 7Tan — AI工具

def main():
    # 1. 最小化监控窗口
    user32.ShowWindow(MONITOR_WND, 6)  # SW_MINIMIZE
    time.sleep(0.5)
    # 2. 恢复并聚焦主窗口
    user32.ShowWindow(MAIN_WND, 9)
    time.sleep(0.3)
    user32.SetForegroundWindow(MAIN_WND)
    time.sleep(0.8)
    # 3. 点击"浏览器"标签 (338,49) 附近多点几次
    for y in (38, 44, 50, 56):
        pyautogui.click(338, y)
        time.sleep(0.5)
    time.sleep(1.0)
    # 4. 截屏
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_minimize_monitor.png')
        print('saved', img.size)
    print('done')

if __name__ == '__main__':
    main()
