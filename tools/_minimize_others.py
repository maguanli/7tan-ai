# -*- coding: utf-8 -*-
"""最小化7Tan/Chrome → 激活微信 → 点击公众号名片"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32

# 最小化 7Tan 和 Chrome
for hwnd, name in [(1508624, "7Tan"), (132624, "Chrome"), (526342, "代码监控")]:
    user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
    time.sleep(0.3)
    print(f"[MIN] {name} 已最小化")

# 激活微信
WX_HWND = 198562
user32.ShowWindow(WX_HWND, 9)
time.sleep(0.3)
user32.SetForegroundWindow(WX_HWND)
time.sleep(0.5)
fg = user32.GetForegroundWindow()
print(f"前台窗口: {fg} (期望 {WX_HWND})")

def grab(box=(-8, -8, 1936, 1056)):
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
    return [(l.text, l.words[0].bounding_rect if l.words else None) for l in res.lines if l.text.strip()]

time.sleep(0.5)
img = grab()
img.save(r"D:\7tan\7tanAI\data\screenshots\wx_after_minimize.png")
texts = [t for t, _ in ocr(img, 2)]
print("\n=== 当前界面 OCR（前10条）===")
for t in texts[:10]:
    print(" ", t)

# 如果微信界面正常，点击公众号名片
if any("手谈" in t for t in texts) or any("微信" in t for t in texts):
    print("\n微信界面可见！点击手谈汉化组名片 (1568,928)")
    pyautogui.click(1568, 928)
    time.sleep(3.0)
    img2 = grab()
    img2.save(r"D:\7tan\7tanAI\data\screenshots\stz_home2.png")
    print("\n=== 点击后 OCR ===")
    for t, r in ocr(img2, 2)[:40]:
        pos = f"({int(r.x/2)},{int(r.y/2)})" if r else ""
        print(f"  {t} {pos}")
else:
    print("\n微信界面不可见，需进一步处理")
