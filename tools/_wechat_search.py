# -*- coding: utf-8 -*-
"""唤出微信搜索框并输入"游戏推荐"，回车搜索"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
import pyperclip

user32 = ctypes.windll.user32

# 1. 激活微信窗口（hwnd=657102）
HWND = 657102
user32.ShowWindow(HWND, 9)
time.sleep(0.2)
user32.SetForegroundWindow(HWND)
time.sleep(0.5)

# 2. 按 Ctrl+F 唤出搜索框（微信4.0全局搜索快捷键）
pyautogui.hotkey("ctrl", "f")
time.sleep(1.0)

# 3. 粘贴输入"游戏推荐"
pyperclip.copy("游戏推荐")
time.sleep(0.3)
pyautogui.hotkey("ctrl", "v")
time.sleep(0.5)
print("[TYPE] 已粘贴: 游戏推荐")

# 4. 截图确认输入是否成功
import mss
from PIL import Image
with mss.mss() as sct:
    shot = sct.grab({"left": 351, "top": 149, "width": 968, "height": 645})
img = Image.frombytes("RGB", shot.size, shot.rgb)
img.save(r"D:\7tan\7tanAI\data\screenshots\wechat_input_check.png")

# 5. OCR 顶部区域确认文字
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.globalization import Language
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
engine = OcrEngine.try_create_from_language(Language("zh-CN"))
if engine is None:
    engine = OcrEngine.try_create_from_user_profile_languages()

def ocr_region(img, box=None):
    if box:
        img = img.crop(box)
    img2 = img.resize((img.width*3, img.height*3), Image.LANCZOS)
    buf = io.BytesIO(); img2.save(buf, format="PNG"); data = buf.getvalue()
    stream = InMemoryRandomAccessStream(); w = DataWriter(stream)
    w.write_bytes(data)
    if hasattr(w, "store"): w.store()
    else: w.store_async().get()
    stream.seek(0)
    decoder = BitmapDecoder.create_async(stream).get()
    bmp = decoder.get_software_bitmap_async().get()
    res = engine.recognize_async(bmp).get()
    return [l.text for l in res.lines if l.text.strip()]

print("=== 顶部区域(0,0,968,150) OCR ===")
for t in ocr_region(img, (0, 0, 968, 150)):
    print(" ", t)
print("=== 全窗口 OCR ===")
for t in ocr_region(img):
    print(" ", t)
