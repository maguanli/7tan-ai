# -*- coding: utf-8 -*-
"""给微信好友 7坛游戏社区 发送问候"""
import sys
import time
import pyautogui
import pyperclip
import pygetwindow as gw

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

def log(msg):
    print(msg, flush=True)

def find_wechat():
    all_wins = gw.getAllWindows()
    for w in all_wins:
        title = w.title.strip()
        if title and ('微信' in title or 'WeChat' in title):
            log(f'找到窗口: {title!r} visible={w.visible} size={w.width}x{w.height}')
            return w
    return None

def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else 'search'
    win = find_wechat()
    if not win:
        log('ERR: 未找到微信窗口')
        return 1

    # 激活微信窗口
    try:
        if win.isMinimized:
            win.restore()
        win.activate()
    except Exception as e:
        log(f'激活异常: {e}')
    time.sleep(1.5)

    # 点击窗口中部空白区确保焦点
    cx = win.left + win.width // 2
    cy = win.top + win.height // 2
    pyautogui.click(cx, cy)
    time.sleep(1.0)
    log(f'OK: 已激活窗口 {win.title!r}，坐标中心=({cx},{cy})')

    if stage == 'search':
        # 打开搜索框
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(1.2)
        pyperclip.copy('7坛游戏社区')
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(2.0)
        log('OK: 已输入搜索词 7坛游戏社区')
        log('NOW_SCREENSHOT_AND_CONFIRM')
    elif stage == 'enter':
        # 搜索结果中回车进入第一个(好友)聊天
        pyautogui.press('enter')
        time.sleep(2.0)
        log('OK: 已按回车进入聊天')
    elif stage == 'send':
        # 点击聊天输入框并发送问候
        cx = win.left + win.width // 2
        cy = win.top + win.height - 120
        pyautogui.click(cx, cy)
        time.sleep(0.8)
        msg = ('嗨，7坛游戏社区的朋友们好！👋 我是CodeLion，'
               '给大家问个好～最近站上有什么好玩的新游戏推荐吗？'
               '祝大家游戏愉快，7坛越办越火！🎮🔥')
        pyperclip.copy(msg)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1.0)
        pyautogui.press('enter')
        time.sleep(1.0)
        log('OK: 问候消息已发送')
    return 0

if __name__ == '__main__':
    sys.exit(main())
