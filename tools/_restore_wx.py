# -*- coding: utf-8 -*-
"""恢复微信主界面：Esc + 截图确认"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102

def activate_wx():
    user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
    user32.SetForegroundWindow(WX_HWND); time.sleep(0.4)

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

activate_wx()
# 按 Esc 返回
pyautogui.press("esc")
time.sleep(0.5)
pyautogui.press("esc")
time.sleep(0.8)

img = grab()
img.save(r"D:\7tan\7tanAI\data\screenshots\wx_restore.png")
print("=== 恢复后界面 OCR ===")
for t in ocr(img, 2)[:30]:
    print(" ", t)
