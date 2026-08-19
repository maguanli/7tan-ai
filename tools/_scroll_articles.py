# -*- coding: utf-8 -*-
"""滚动公众号文章列表，OCR 抓取标题+阅读量，找10万+爆款"""
import ctypes, sys, io, time, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102

def activate_wx():
    user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
    user32.SetForegroundWindow(WX_HWND); time.sleep(0.4)
    return user32.GetForegroundWindow() == WX_HWND

def grab(box=(351, 149, 968, 645)):
    with mss.mss() as sct:
        shot = sct.grab({"left": box[0], "top": box[1], "width": box[2], "height": box[3]})
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
time.sleep(0.3)

# 鼠标移到文章列表区域
pyautogui.moveTo(700, 520)
time.sleep(0.3)

seen = set()
found = []
for round_i in range(12):
    if not activate_wx():
        print("微信失焦，重新激活")
    img = grab()
    texts = ocr(img, 2, (480, 280, 960, 645))
    joined = "\n".join(texts)
    # 抓标题行（较长）和阅读行
    for t in texts:
        if "阅读" in t or "10万" in t:
            print(f"  [阅读] {t}")
            found.append(t)
        elif len(t) > 12 and not re.search(r"原创|私信|全部|贴图", t):
            key = t[:15]
            if key not in seen:
                seen.add(key)
                print(f"  [标题] {t}")
    # 滚动
    pyautogui.scroll(-4)
    time.sleep(0.6)

print(f"\n=== 共抓到 {len(found)} 条阅读数据 ===")
