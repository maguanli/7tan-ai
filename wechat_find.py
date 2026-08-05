# -*- coding: utf-8 -*-
"""探测微信窗口位置，并测试截图链路"""
import sys, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pygetwindow as gw
import pyautogui

all_wins = gw.getAllTitles()
wechat_wins = [t for t in all_wins if t and ('微信' in t or 'WeChat' in t or 'wechat' in t.lower())]
print('=== 含微信的窗口 ===')
for t in wechat_wins:
    print(repr(t))

target = None
for t in wechat_wins:
    try:
        w = gw.getWindowsWithTitle(t)
        if w and w[0].visible:
            target = w[0]
            print('选定窗口:', repr(t), '位置:', target.left, target.top, '尺寸:', target.width, target.height)
            break
    except Exception as e:
        print('获取窗口失败', t, e)

if target:
    try:
        target.activate()
        time.sleep(1.0)
        region = (target.left, target.top, target.width, target.height)
        img = pyautogui.screenshot(region=region)
        out = r'D:\7tan\7tanAI\wechat_screen.png'
        img.save(out)
        print('截图已保存:', out, img.size)
    except Exception as e:
        print('截图失败:', e)
else:
    print('未找到可见微信窗口')
