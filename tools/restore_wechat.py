# -*- coding: utf-8 -*-
"""查找微信窗口（含隐藏），恢复并前置显示"""
import ctypes, time, sys
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass
import win32gui, win32con

hits = []
def cb(hwnd, _):
    title = win32gui.GetWindowText(hwnd)
    cls = win32gui.GetClassName(hwnd)
    if ('微信' in title) or ('Weixin' in cls.lower()) or ('wechat' in cls.lower()) or ('WeChat' in cls):
        import win32process
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        try:
            rect = win32gui.GetWindowRect(hwnd)
        except Exception:
            rect = (0,0,0,0)
        hits.append({
            'hwnd': hwnd, 'title': title, 'cls': cls, 'rect': rect,
            'visible': win32gui.IsWindowVisible(hwnd),
            'iconic': win32gui.IsIconic(hwnd),
            'pid': pid,
        })
win32gui.EnumWindows(cb, None)

print(f"FOUND={len(hits)}")
for h in hits:
    print(f"hwnd={h['hwnd']} visible={h['visible']} iconic={h['iconic']} rect={h['rect']} title={h['title']!r} cls={h['cls']} pid={h['pid']}")

# 找微信主窗口：优先可见、非图标、面积大；否则任意
cands = [h for h in hits if h['visible'] and not h['iconic']]
if not cands:
    cands = hits
if not cands:
    print("NO_WECHAT")
    sys.exit(1)

cands.sort(key=lambda h: (h['rect'][2]-h['rect'][0])*(h['rect'][3]-h['rect'][1]), reverse=True)
target = cands[0]
hwnd = target['hwnd']
print(f"TARGET hwnd={hwnd} title={target['title']!r}")

# 恢复并前置
try:
    if target['iconic']:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(1.0)
    # 再次确认
    print("AFTER:", win32gui.IsWindowVisible(hwnd), win32gui.GetWindowRect(hwnd))
except Exception as e:
    print("ACTIVATE_ERR:", e)
print("DONE")
