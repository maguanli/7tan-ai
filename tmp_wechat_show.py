# -*- coding: utf-8 -*-
import io, win32gui, win32con, win32process, ctypes, time

out = io.open(r"D:\7tan\7tanAI\tmp_winlist.txt", "w", encoding="utf-8")
user32 = ctypes.windll.user32
TARGET_PID = 9056

found = []
def enum_cb(hwnd, r):
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
    except Exception:
        return
    if pid != TARGET_PID:
        return
    t = win32gui.GetWindowText(hwnd)
    cls = win32gui.GetClassName(hwnd)
    vis = win32gui.IsWindowVisible(hwnd)
    found.append((hwnd, cls, t, vis))
    out.write("hwnd=%s cls=%s vis=%s title=%s\n" % (hwnd, cls, vis, t))

win32gui.EnumWindows(enum_cb, None)
out.write("TOTAL: %d\n" % len(found))

# 尝试显示每个窗口（优先有标题/类名像主窗口的）
for hwnd, cls, t, vis in found:
    if 'Qt' in cls and (t or True):
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        except Exception as e:
            out.write("show err %r\n" % e)

time.sleep(1.0)
# 重新检查可见性
for hwnd, cls, t, vis in found:
    out.write("AFTER vis=%s title=%s\n" % (win32gui.IsWindowVisible(hwnd), win32gui.GetWindowText(hwnd)))
out.close()
print("DONE")
