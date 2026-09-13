# -*- coding: utf-8 -*-
"""完整流程：点击搜索框→粘贴游戏推荐→回车→OCR结果页"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui, pyperclip
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102

def activate_wx():
    user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
    user32.SetForegroundWindow(WX_HWND); time.sleep(0.4)

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
    return [(l.text, l.words[0].bounding_rect if l.words else None) for l in res.lines if l.text.strip()]

# 1. 激活并等待
activate_wx()
time.sleep(1.0)
img = grab()
img.save(r"D:\7tan\7tanAI\data\screenshots\step1_wx.png")
print("=== 步骤1 当前界面 ===")
for t, r in ocr(img, 2)[:20]:
    pos = f"({int(r.x/2)},{int(r.y/2)})" if r else ""
    print(f"  {t} {pos}")

# 2. 点击搜索框
pyautogui.click(545, 205)
time.sleep(0.8)
print("\n[CLICK] 搜索框 (545,205)")

# 3. 粘贴输入（清空后输入）
pyperclip.copy("游戏推荐")
time.sleep(0.3)
pyautogui.hotkey("ctrl", "a")
time.sleep(0.2)
pyautogui.hotkey("ctrl", "v")
time.sleep(0.5)
print("[TYPE] 已粘贴: 游戏推荐")

# 4. 截图确认输入
img2 = grab((411, 179, 260, 85))
img2.save(r"D:\7tan\7tanAI\data\screenshots\step2_typed.png")
print("\n=== 步骤2 搜索框区域 OCR ===")
for t, r in ocr(img2, 3):
    print(f"  {t}")

# 5. 回车
pyautogui.press("enter")
time.sleep(2.5)
print("\n[ENTER] 已回车")

# 6. 截图结果页
img3 = grab()
img3.save(r"D:\7tan\7tanAI\data\screenshots\step3_result.png")
print("\n=== 步骤3 搜索结果页 OCR ===")
for t, r in ocr(img3, 2)[:35]:
    pos = f"({int(r.x/2)},{int(r.y/2)})" if r else ""
    print(f"  {t} {pos}")
