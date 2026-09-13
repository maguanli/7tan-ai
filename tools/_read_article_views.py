# -*- coding: utf-8 -*-
"""滚动右侧文章 + OCR 查找阅读量"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102
user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
user32.SetForegroundWindow(WX_HWND); time.sleep(0.3)

# 鼠标移到右侧文章区域
pyautogui.moveTo(950, 500)
time.sleep(0.3)

def grab():
    with mss.mss() as sct:
        shot = sct.grab({"left": 351, "top": 149, "width": 968, "height": 645})
    return Image.frombytes("RGB", shot.size, shot.rgb)

def ocr(img, scale=2, region=None):
    if region:
        img = img.crop(region)
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

# 1. 先 OCR 当前右侧文章标题区域（找"阅读"）
img = grab()
print("=== 文章顶部区域 OCR（找阅读量）===")
texts = ocr(img, 3, (480, 80, 960, 380))
for t in texts:
    print(" ", t)

# 2. 滚动到底部（可能阅读量在底部）
for i in range(8):
    pyautogui.scroll(-3)
    time.sleep(0.3)

time.sleep(0.8)
img = grab()
img.save(r"D:\7tan\7tanAI\data\screenshots\article_bottom.png")
print("\n=== 滚动后（底部）OCR ===")
texts = ocr(img, 2)
for t in texts[-25:]:
    print(" ", t)
