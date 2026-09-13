# -*- coding: utf-8 -*-
"""点击微信窗口内多个位置，尝试恢复渲染"""
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

def ocr(img, scale=2):
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
time.sleep(0.5)

clicks = [
    (445, 198, "返回箭头(公众号)"),
    (700, 400, "窗口中央"),
    (430, 200, "左侧栏顶部"),
    (700, 500, "右侧中部"),
    (500, 700, "左下角"),
]
for cx, cy, desc in clicks:
    pyautogui.click(cx, cy)
    time.sleep(0.8)
    img = grab()
    texts = ocr(img, 2)
    joined = " | ".join(texts[:6])
    print(f"点击({cx},{cy})[{desc}] → OCR: {joined[:100]}")
    if len(texts) > 4:
        print("  ✅ 界面内容恢复正常！")
        img.save(r"D:\7tan\7tanAI\data\screenshots\wx_recovered.png")
        break
    time.sleep(0.3)
