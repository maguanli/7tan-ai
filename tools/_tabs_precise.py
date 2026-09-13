# -*- coding: utf-8 -*-
"""精确定位Tab行：放大OCR y=155~205"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 198562
WL, WT = -8, -8

def activate_wx():
    user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
    user32.SetForegroundWindow(WX_HWND); time.sleep(0.4)

def grab(box=(WL, WT, 1936, 1056)):
    with mss.mss() as sct:
        shot = sct.grab({"left": box[0], "top": box[1], "width": box[2], "height": box[3]})
    return Image.frombytes("RGB", shot.size, shot.rgb)

def ocr(img, scale=4, region=None):
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

activate_wx()
time.sleep(0.3)
img = grab()

print("=== Tab行放大OCR (1450,150)-(1936,210) ===")
for t, r in ocr(img, 4, (1450, 150, 1936, 210)):
    # 还原坐标：相对窗口 = r/4 + region偏移
    x = int(r.x/4) + 1450
    y = int(r.y/4) + 150
    w = int(r.width/4)
    print(f"  '{t}'  x={x} y={y} w={w}  中心x={x+w//2}")

print("\n=== 排序行放大OCR (1450,205)-(1936,250) ===")
for t, r in ocr(img, 4, (1450, 205, 1936, 250)):
    x = int(r.x/4) + 1450
    y = int(r.y/4) + 205
    w = int(r.width/4)
    print(f"  '{t}'  x={x} y={y} w={w}  中心x={x+w//2}")
