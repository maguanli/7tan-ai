# -*- coding: utf-8 -*-
import ctypes, time, io, win32gui, win32con
import mss

out = io.open(r"D:\7tan\7tanAI\tmp_wechat_out.txt", "w", encoding="utf-8")
user32 = ctypes.windll.user32
HWND = 2426392

# 强制前台
fg = user32.GetForegroundWindow()
target_tid = user32.GetWindowThreadProcessId(HWND, None)
me = user32.GetWindowThreadProcessId(fg, None) if fg else 0
if fg:
    user32.AttachThreadInput(me, target_tid, True)
user32.ShowWindow(HWND, win32con.SW_RESTORE)
user32.BringWindowToTop(HWND)
user32.SetForegroundWindow(HWND)
time.sleep(0.3)
if fg:
    user32.AttachThreadInput(me, target_tid, False)
time.sleep(1.2)
out.write("FG: %s\n" % user32.GetForegroundWindow())
out.write("TITLE: %s\n" % win32gui.GetWindowText(HWND))
out.close()

# 截图
with mss.mss() as sct:
    img = sct.grab(sct.monitors[1])
    mss.tools.to_png(img.rgb, img.size, output=r"D:\7tan\7tanAI\tmp_wechat_screen.png")
print("DONE")
