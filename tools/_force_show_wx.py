# -*- coding: utf-8 -*-
"""强制恢复微信窗口显示"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes.wintypes as wt
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 198562

# 各种方式恢复
print("尝试恢复微信窗口...")
user32.ShowWindow(WX_HWND, 4)   # SW_SHOWNOACTIVATE
time.sleep(0.3)
user32.ShowWindow(WX_HWND, 9)   # SW_RESTORE
time.sleep(0.5)
user32.ShowWindow(WX_HWND, 3)   # SW_MAXIMIZE
time.sleep(0.8)
user32.SetForegroundWindow(WX_HWND)
time.sleep(0.5)

print(f"IsWindowVisible: {user32.IsWindowVisible(WX_HWND)}")
print(f"IsIconic(最小化): {user32.IsIconic(WX_HWND)}")
print(f"前台: {user32.GetForegroundWindow()}")

rect = wt.RECT()
user32.GetWindowRect(WX_HWND, ctypes.byref(rect))
print(f"窗口位置: ({rect.left},{rect.top})-({rect.right},{rect.bottom})")

with mss.mss() as sct:
    shot = sct.grab({"left": rect.left, "top": rect.top,
                     "width": max(1, rect.right-rect.left), "height": max(1, rect.bottom-rect.top)})
img = Image.frombytes("RGB", shot.size, shot.rgb)
img.save(r"D:\7tan\7tanAI\data\screenshots\wx_forced.png")

def ocr(img, scale=2):
    img2 = img.resize((img.width*scale, img.height*scale), Image.LANCZOS)
    buf = io.BytesIO(); img2.save(buf, format="PNG"); data = buf.getvalue()
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
    engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    stream = InMemoryRandomAccessStream(); w = DataWriter(stream)
    w.write_bytes(data)
    if hasattr(w, "store"): w.store()
    else: w.store_async().get()
    stream.seek(0)
    decoder = BitmapDecoder.create_async(stream).get()
    bmp = decoder.get_software_bitmap_async().get()
    res = engine.recognize_async(bmp).get()
    return [l.text for l in res.lines if l.text.strip()]

print("\n=== 微信窗口 OCR ===")
for t in ocr(img, 2)[:20]:
    print(" ", t)
