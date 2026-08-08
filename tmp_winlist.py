# -*- coding: utf-8 -*-
import io, win32gui, win32process

out = io.open(r"D:\7tan\7tanAI\tmp_winlist.txt", "w", encoding="utf-8")

def enum_cb(hwnd, r):
    if not win32gui.IsWindowVisible(hwnd):
        return
    t = win32gui.GetWindowText(hwnd)
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
    except Exception:
        pid = -1
    out.write("%s | pid=%s | %s | %s\n" % (hwnd, pid, win32gui.GetClassName(hwnd), t))

win32gui.EnumWindows(enum_cb, None)
out.close()
print("DONE")
