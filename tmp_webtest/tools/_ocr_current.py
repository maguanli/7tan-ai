# -*- coding: utf-8 -*-
"""OCR 查看当前微信界面（搜索后）"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102
user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
user32.SetForegroundWindow(WX_HWND); time.sleep(0.3)

with mss.mss() as sct:
    shot = sct.grab({"left": 351, "top": 149, "width": 968, "height": 645})
img = Image.frombytes("RGB", shot.size, shot.rgb)
img.save(r"D:\7tan\7tanAI\data\screenshots\current_wx.png")

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
    if engine is None:
        engine = OcrEngine.try_create_from_user_profile_languages()
    stream = InMemoryRandomAccessStream(); w = DataWriter(stream)
    w.write_bytes(data)
    if hasattr(w, "store"): w.store()
    else: w.store_async().get()
    stream.seek(0)
    decoder = BitmapDecoder.create_async(stream).get()
    bmp = decoder.get_software_bitmap_async().get()
    res = engine.recognize_async(bmp).get()
    out = []
    for line in res.lines:
        t = line.text.strip()
        if t:
            # 第一行第一个词的坐标
            r = line.words[0].bounding_rect if line.words else None
            out.append((t, (int(r.x/scale), int(r.y/scale)) if r else None))
    return out

print("=== 全窗口 OCR ===")
for t, pos in ocr(img, 2)[:30]:
    print(f"  {t}  {pos}")

print("\n=== 左侧栏 OCR（搜索框区域 x=60-320）===")
for t, pos in ocr(img, 3, (60, 30, 260, 150)):
    print(f"  {t}  {pos}")
