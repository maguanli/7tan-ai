# -*- coding: utf-8 -*-
"""精确点击文章Tab(1626,164) + 找最热排序"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
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

def ocr(img, scale=3, region=None):
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

# 点击文章 Tab（绝对坐标）
ax, ay = 1626, 164
pyautogui.click(ax, ay)
time.sleep(2.5)
print(f"[CLICK] 文章Tab ({ax},{ay})")

img = grab()
img.save(r"D:\7tan\7tanAI\data\screenshots\article_tab2.png")

# 顶部区域
print("\n=== 顶部 (1460,90)-(1936,280) ===")
for t, r in ocr(img, 3, (1460, 90, 1936, 280)):
    pos = f"({int(r.x/3)+1460},{int(r.y/3)+90})" if r else ""
    print(f"  {t} {pos}")

# 列表区域
print("\n=== 列表区域 (1460,280)-(1936,700) ===")
for t, r in ocr(img, 2, (1460, 280, 1936, 700)):
    pos = f"({int(r.x/2)+1460},{int(r.y/2)+280})" if r else ""
    print(f"  {t} {pos}")
