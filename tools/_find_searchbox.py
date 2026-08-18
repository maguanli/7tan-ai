# -*- coding: utf-8 -*-
"""截取微信窗口顶部区域，定位搜索框"""
import ctypes, sys, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mss
from PIL import Image

# 微信窗口位置（上一步已知）
left, top, right, bottom = 351, 149, 1319, 794
W = right - left
H = bottom - top

# 顶部区域：左侧栏(0-260)的顶部 150px + 右侧顶部
# 微信4.0 搜索框通常在左上角区域
regions = {
    "左上(搜索区)": (left, top, 300, 120),
    "顶部全宽": (left, top, W, 90),
    "左侧栏": (left, top, 300, H),
}
imgs = {}
with mss.mss() as sct:
    for name, (x, y, w, h) in regions.items():
        shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        imgs[name] = img

# OCR 每个区域（放大2倍）
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.globalization import Language
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

engine = OcrEngine.try_create_from_language(Language("zh-CN"))
if engine is None:
    engine = OcrEngine.try_create_from_user_profile_languages()

def ocr(img):
    img2 = img.resize((img.width*2, img.height*2), Image.LANCZOS)
    buf = io.BytesIO(); img2.save(buf, format="PNG"); data = buf.getvalue()
    stream = InMemoryRandomAccessStream(); w = DataWriter(stream)
    w.write_bytes(data)
    if hasattr(w, "store"): w.store()
    else: w.store_async().get()
    stream.seek(0)
    decoder = BitmapDecoder.create_async(stream).get()
    bmp = decoder.get_software_bitmap_async().get()
    res = engine.recognize_async(bmp).get()
    return [(l.text, l.words[0].bounding_rect if l.words else None) for l in res.lines if l.text.strip()]

for name, img in imgs.items():
    print(f"===== {name} =====")
    for text, rect in ocr(img):
        r = f" (x={rect.x/2:.0f} y={rect.y/2:.0f} w={rect.width/2:.0f} h={rect.height/2:.0f})" if rect else ""
        print(f"  {text}{r}")
    print()
