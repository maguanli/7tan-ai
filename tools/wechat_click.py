# -*- coding: utf-8 -*-
"""
wechat_click.py — 微信自动化操作：激活窗口 → 点击(相对/绝对坐标) → 可选输入文字
用法:
  python wechat_click.py click 831 224            # 绝对坐标点击
  python wechat_click.py click_rel 0.5 0.12       # 窗口相对位置点击(比例)
  python wechat_click.py type "游戏推荐"           # 输入文字(需先点击)
  python wechat_click.py key enter                 # 按键
  python wechat_click.py combo ctrl,f              # 组合键
"""
import sys, ctypes, time
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass
import win32gui, win32con
import pyautogui

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.15

def find_main_window():
    hits = []
    def cb(hwnd, _):
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        if ('微信' in title) or ('weixin' in cls.lower()) or ('wechat' in cls.lower()):
            try:
                rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                return
            w, h = rect[2]-rect[0], rect[3]-rect[1]
            if w > 100 and h > 100:
                hits.append((hwnd, title, rect, w, h))
    win32gui.EnumWindows(cb, None)
    if not hits:
        return None
    hits.sort(key=lambda x: x[3]*x[4], reverse=True)
    return hits[0]

def activate(hwnd):
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.8)

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'click'
    win = find_main_window()
    if not win:
        print("NO_WECHAT_WINDOW")
        return 1
    hwnd, title, rect, w, h = win
    print(f"WINDOW hwnd={hwnd} rect={rect} size={w}x{h}")

    if cmd == 'click':
        x, y = int(sys.argv[2]), int(sys.argv[3])
        activate(hwnd)
        pyautogui.click(x, y)
        print(f"CLICK {x},{y}")
    elif cmd == 'click_rel':
        rx, ry = float(sys.argv[2]), float(sys.argv[3])
        activate(hwnd)
        x = rect[0] + int(w * rx)
        y = rect[1] + int(h * ry)
        pyautogui.click(x, y)
        print(f"CLICK_REL {rx},{ry} -> {x},{y}")
    elif cmd == 'type':
        activate(hwnd)
        text = sys.argv[2]
        pyautogui.write(text, interval=0.05)
        print(f"TYPE {text}")
    elif cmd == 'key':
        activate(hwnd)
        key = sys.argv[2]
        pyautogui.press(key)
        print(f"KEY {key}")
    elif cmd == 'combo':
        activate(hwnd)
        keys = sys.argv[2].split(',')
        pyautogui.hotkey(*keys)
        print(f"COMBO {keys}")
    elif cmd == 'scroll':
        activate(hwnd)
        clicks = int(sys.argv[2]) if len(sys.argv) > 2 else -3
        pyautogui.scroll(clicks * 120)  # 负=向下
        print(f"SCROLL {clicks}")
    else:
        print("UNKNOWN_CMD", cmd)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
