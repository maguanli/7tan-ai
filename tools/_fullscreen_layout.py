# -*- coding: utf-8 -*-
"""截全屏看整体布局，定位微信窗口实际位置"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes.wintypes as wt
from PIL import Image
import mss

user32 = ctypes.windll.user32

# 枚举微信相关窗口的实际 rect
for hwnd, name in [(198562, "Weixin#1"), (1509102, "微信#2"), (133020, "Weixin#3")]:
    rect = wt.RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        vis = user32.IsWindowVisible(hwnd)
        icon = user32.IsIconic(hwnd)
        print(f"{name}: hwnd={hwnd} rect=({rect.left},{rect.top})-({rect.right},{rect.bottom}) visible={vis} min={icon}")

# 全屏截图（monitor 0 全部）
with mss.mss() as sct:
    m = sct.monitors[0]  # 所有显示器合并
    shot = sct.grab({"left": m["left"], "top": m["top"], "width": m["width"], "height": m["height"]})
img = Image.frombytes("RGB", shot.size, shot.rgb)
print(f"\n全屏截图尺寸: {img.size}")
img.save(r"D:\7tan\7tanAI\data\screenshots\fullscreen_all.png")

# OCR 全屏（缩小到半屏再识别，看整体）
img2 = img.resize((img.width//2, img.height//2), Image.LANCZOS)
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
print("=== 全屏 OCR（坐标×2还原）===")
for l in res.lines:
    if l.text.strip():
        r = l.words[0].bounding_rect if l.words else None
        pos = f"({int(r.x*2)},{int(r.y*2)})" if r else ""
        print(f"  '{l.text}' {pos}")
