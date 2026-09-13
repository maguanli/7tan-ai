# -*- coding: utf-8 -*-
"""微信完整搜索流程：搜索框→游戏推荐→回车→结果页(找文章/最热)"""
import ctypes, sys, io, time, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui, pyperclip
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 198562  # 微信主窗口(最大化)

# 窗口坐标
WL, WT, WW, WH = -8, -8, 1936, 1056

def activate_wx():
    user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
    user32.SetForegroundWindow(WX_HWND); time.sleep(0.4)

def grab(box=(WL, WT, WW, WH)):
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

activate_wx()
time.sleep(0.5)

# 1. 点击搜索框（相对窗口 (194,56) → 绝对 (WL+194, WT+56)）
sx, sy = WL + 194, WT + 56
pyautogui.click(sx, sy)
time.sleep(0.8)
print(f"[CLICK] 搜索框 ({sx},{sy})")

# 2. 输入"游戏推荐"
pyperclip.copy("游戏推荐")
time.sleep(0.3)
pyautogui.hotkey("ctrl", "a"); time.sleep(0.2)
pyautogui.hotkey("ctrl", "v"); time.sleep(0.5)
print("[TYPE] 游戏推荐")

# 3. 截图确认输入（搜索框区域）
img = grab((WL+60, WT+30, 300, 90))
img.save(r"D:\7tan\7tanAI\data\screenshots\input_check2.png")
texts = ocr(img, 3)
print("搜索框区域OCR:", texts)

# 4. 回车
pyautogui.press("enter")
time.sleep(3.0)
print("[ENTER] 回车")

# 5. 结果页全窗口 OCR
img2 = grab()
img2.save(r"D:\7tan\7tanAI\data\screenshots\result_v3.png")
print("\n=== 搜索结果页 OCR（前45条）===")
for t, r in ocr(img2, 2)[:45]:
    pos = f"({int(r.x/2)},{int(r.y/2)})" if r else ""
    print(f"  {t} {pos}")
