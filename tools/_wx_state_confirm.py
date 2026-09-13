# -*- coding: utf-8 -*-
"""重新激活微信并确认界面状态"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102

# 激活微信（多种方式）
for m in range(3):
    user32.ShowWindow(WX_HWND, 9); time.sleep(0.3)
    user32.SetForegroundWindow(WX_HWND); time.sleep(0.5)
    fg = user32.GetForegroundWindow()
    if fg == WX_HWND:
        print(f"[OK] 微信已激活 (第{m}次)")
        break
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
    return [(l.text, l.words[0].bounding_rect if l.words else None) for l in res.lines if l.text.strip()]

img = grab()
img.save(r"D:\7tan\7tanAI\data\screenshots\wx_state_confirm.png")
print("\n=== 当前微信界面 OCR ===")
for t, r in ocr(img, 2)[:35]:
    pos = f"({int(r.x/2)},{int(r.y/2)})" if r else ""
    print(f"  {t}  {pos}")
