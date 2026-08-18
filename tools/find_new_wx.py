# -*- coding: utf-8 -*-
"""自动查找微信主窗口 + 截图 OCR（新句柄）"""
import sys, io, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctypes.windll.shcore.SetProcessDpiAwareness(1)
sys.path.insert(0, r'D:\7tan\7tanAI\tools')
from PIL import Image
import win32gui, mss
import wechat_scan as ws

def find_wechat_main():
    hits = []
    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        if ('微信' in title) or ('weixin' in cls.lower()) or ('wechat' in cls.lower()):
            try:
                rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                return
            w, h = rect[2]-rect[0], rect[3]-rect[1]
            if w > 100 and h > 100:
                hits.append((hwnd, title, cls, rect, w, h))
    win32gui.EnumWindows(cb, None)
    if not hits:
        return None
    hits.sort(key=lambda x: x[4]*x[5], reverse=True)
    return hits[0]

win = find_wechat_main()
if not win:
    print("NO_WECHAT")
    sys.exit(1)
hwnd, title, cls, rect, w, h = win
print(f"WX hwnd={hwnd} title={title!r} cls={cls} rect={rect} size={w}x{h}")

x0, y0, x1, y1 = rect
with mss.MSS() as sct:
    shot = sct.grab({'left': x0, 'top': y0, 'width': w, 'height': h})
img = Image.frombytes('RGB', shot.size, shot.rgb)
img.save(r'D:\7tan\7tanAI\tools\ocr_work\new_wx.png')
big = img.resize((int(img.width*2), int(img.height*2)), Image.LANCZOS)
words, text = ws.ocr_words(big, scale=2.0)
print("=== 新窗口界面 ===")
print(text[:250])
with open(r'D:\7tan\7tanAI\tools\ocr_work\new_wx.txt', 'w', encoding='utf-8') as f:
    for wx, wy, ww, wh, wt in words:
        f.write(f"({wx},{wy},{ww},{wh}) | {wt}\n")
    f.write("\nFULL:\n" + text)
