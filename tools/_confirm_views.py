# -*- coding: utf-8 -*-
"""精确放大OCR确认阅读量"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image, ImageOps, ImageEnhance
import mss

user32 = ctypes.windll.user32
WX_HWND = 198562
WL, WT = -8, -8

def activate_wx():
    user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
    user32.SetForegroundWindow(WX_HWND); time.sleep(0.3)

def grab(box=(WL, WT, 1936, 1056)):
    with mss.mss() as sct:
        shot = sct.grab({"left": box[0], "top": box[1], "width": box[2], "height": box[3]})
    return Image.frombytes("RGB", shot.size, shot.rgb)

def ocr_enhanced(img, scale=4):
    img = img.resize((img.width*scale, img.height*scale), Image.LANCZOS)
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = ImageEnhance.Contrast(img).enhance(2.0)
    buf = io.BytesIO(); img.save(buf, format="PNG"); data = buf.getvalue()
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

# 阅读量区域：相对窗口 (950, 830)-(1400, 950) 放大确认
print("=== 阅读量区域放大OCR (950,830)-(1400,950) ===")
for t, r in ocr_enhanced(img.crop((950, 830, 1400, 950)), 4):
    x = int(r.x/4)+950; y = int(r.y/4)+830
    print(f"  '{t}' ({x},{y})")

# 也确认公众号名片区域
print("\n=== 公众号名片区域 (1450,880)-(1936,1020) ===")
for t, r in ocr_enhanced(img.crop((1450, 880, 1936, 1020)), 4):
    x = int(r.x/4)+1450; y = int(r.y/4)+880
    print(f"  '{t}' ({x},{y})")
