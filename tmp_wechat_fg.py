# -*- coding: utf-8 -*-
import ctypes, time, io
import win32gui, win32con, win32process

out = io.open(r"D:\7tan\7tanAI\tmp_wechat_out.txt", "w", encoding="utf-8")

user32 = ctypes.windll.user32

def find_wechat():
    wins = []
    def cb(h, r):
        if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h) == '微信':
            wins.append(h)
    win32gui.EnumWindows(cb, None)
    return wins

def force_foreground(hwnd):
    # AttachThreadInput 方法强制前台
    fg = user32.GetForegroundWindow()
    me = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
    target_tid = user32.GetWindowThreadProcessId(hwnd, None)
    try:
        if fg:
            user32.AttachThreadInput(me, target_tid, True)
        user32.ShowWindow(hwnd, win32con.SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.2)
        if fg:
            user32.AttachThreadInput(me, target_tid, False)
    except Exception as e:
        out.write("FORE_ERR %r\n" % e)

wins = find_wechat()
out.write("WINS: %s\n" % (wins,))
if wins:
    h = wins[0]
    force_foreground(h)
    time.sleep(1.0)
    out.write("FOREGROUND: %s\n" % user32.GetForegroundWindow())
    out.write("TITLE: %s\n" % win32gui.GetWindowText(h))
    rect = win32gui.GetWindowRect(h)
    out.write("RECT: %s\n" % (rect,))
    if win32gui.IsIconic(h):
        out.write("IS_ICONIC\n")
else:
    out.write("NO_WECHAT\n")
out.close()
print("DONE")
