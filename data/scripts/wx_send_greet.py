# -*- coding: utf-8 -*-
"""发送问候到微信好友 7坛游戏社区"""
import sys, time

def log(*args):
    print(*args, flush=True)

try:
    import win32gui, win32con, win32clipboard, win32api
except ImportError as e:
    log('IMPORT_FAIL:', e)
    sys.exit(3)

def find_wechat():
    result = []
    def cb(hwnd, extra):
        try:
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if '微信' in t or 'WeChat' in t:
                    result.append((hwnd, t))
        except Exception:
            pass
    win32gui.EnumWindows(cb, None)
    return result

def set_clip(t):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(t, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()

def key(vk, up=False):
    win32api.keybd_event(vk, 0, 2 if up else 0, 0)

def combo(vk):
    key(0x11); key(vk); key(vk, True); key(0x11, True)

def main():
    log('STEP1 find wechat window')
    wins = find_wechat()
    log('wins:', wins)
    if not wins:
        log('ERROR: no wechat window found')
        return 1
    hwnd = wins[0][0]
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.6)
    log('STEP2 activate done')

    # Ctrl+F 打开搜索
    combo(0x46)  # F
    time.sleep(0.7)
    log('STEP3 search opened')

    # 输入搜索关键词
    set_clip('7坛游戏社区')
    combo(0x56)  # V
    time.sleep(0.7)
    log('STEP4 keyword pasted')

    # 回车进入聊天
    key(0x0D); key(0x0D, True)
    time.sleep(0.8)
    log('STEP5 chat opened')

    # 粘贴问候语
    msg = '大家好！祝7坛游戏社区越来越红火，各位玩得开心！最近有什么好玩的游戏，欢迎推荐分享～'
    set_clip(msg)
    combo(0x56)  # V
    time.sleep(0.4)
    log('STEP6 msg pasted')

    # 回车发送
    key(0x0D); key(0x0D, True)
    time.sleep(0.5)
    log('STEP7 SENT_OK')
    return 0

if __name__ == '__main__':
    sys.exit(main())
