# -*- coding: utf-8 -*-
"""快速给微信好友发问候：窗口还在就直接发，不重新搜索"""
import win32gui, win32con, win32clipboard, time, sys, os

SCREENSHOT_DIR = r'D:\7tan\7tanAI\data\screenshots'
LOG = os.path.join(SCREENSHOT_DIR, 'wx_send_fast_log.txt')

def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S') + ' ' + msg + '\n')

def find_wx_windows():
    results = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if '微信' in t:
                results.append((hwnd, t))
    win32gui.EnumWindows(cb, None)
    return results

def screenshot(name):
    try:
        import mss
        with mss.mss() as sct:
            mon = sct.monitors[1]
            img = sct.grab(mon)
            path = os.path.join(SCREENSHOT_DIR, name)
            mss.tools.to_png(img.rgb, img.size, output=path)
            return path
    except Exception as e:
        log('截图失败: %s' % e)
        return None

def set_clipboard(text):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()

def main():
    log('=== 开始快速发送 ===')
    wins = find_wx_windows()
    log('微信窗口: %s' % wins)
    if not wins:
        log('未找到微信窗口')
        print('NO_WINDOW')
        return
    hwnd = wins[0][0]
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.6)
    # 截屏确认当前聊天对象（窗口应该还停在7坛游戏社区）
    shot1 = screenshot('wx_fast_before.png')
    log('发送前截图: %s' % shot1)
    # 输入问候语
    msg = '大家好！祝7坛游戏社区越来越红火，各位玩得开心！最近有什么好玩的游戏，欢迎推荐分享～🎮'
    set_clipboard(msg)
    log('剪贴板已写入问候语')
    time.sleep(0.3)
    # 模拟 Ctrl+V 粘贴 + 回车发送（输入框大概率还在聚焦状态）
    win32api = __import__('win32api')
    win32api.keybd_event(0x11, 0, 0, 0)  # Ctrl
    win32api.keybd_event(0x56, 0, 0, 0)  # V
    win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(0.8)
    win32api.keybd_event(0x0D, 0, 0, 0)  # Enter
    win32api.keybd_event(0x0D, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(1.0)
    shot2 = screenshot('wx_fast_after.png')
    log('发送后截图: %s' % shot2)
    print('SENT')

if __name__ == '__main__':
    main()
