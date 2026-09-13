# -*- coding: utf-8 -*-
"""精确点击搜索框(545,205) + 粘贴输入 + 增强OCR验证"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui, pyperclip
from PIL import Image, ImageOps, ImageEnhance
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102
user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
user32.SetForegroundWindow(WX_HWND); time.sleep(0.5)

def grab_box(box):
    with mss.mss() as sct:
        shot = sct.grab({"left": box[0], "top": box[1], "width": box[2], "height": box[3]})
    return Image.frombytes("RGB", shot.size, shot.rgb)

def ocr_enhanced(img, scale=5):
    # 图像增强：放大 + 灰度 + 对比度 + 锐化
    img = img.resize((img.width*scale, img.height*scale), Image.LANCZOS)
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.point(lambda p: 255 if p > 140 else 0)  # 二值化
    buf = io.BytesIO(); img.save(buf, format="PNG"); data = buf.getvalue()
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
    return [l.text for l in res.lines if l.text.strip()]

# 搜索框区域（绝对坐标）
BOX = (351+60, 149+30, 260, 85)  # x=411, y=179, w=260, h=85

print("=== 点击前 搜索框区域 OCR（增强5倍）===")
img0 = grab_box(BOX)
for t in ocr_enhanced(img0):
    print("  ", t)

# 精确点击搜索框中心
cx, cy = 545, 205
pyautogui.click(cx, cy)
time.sleep(1.0)
print(f"\n[CLICK] ({cx},{cy}) 搜索框")

print("\n=== 点击后 搜索框区域 OCR ===")
img1 = grab_box(BOX)
for t in ocr_enhanced(img1):
    print("  ", t)

# 粘贴输入
pyperclip.copy("游戏推荐")
time.sleep(0.3)
pyautogui.hotkey("ctrl", "v")
time.sleep(0.8)
print("\n[TYPE] 已粘贴: 游戏推荐")

print("\n=== 输入后 搜索框区域 OCR ===")
img2 = grab_box(BOX)
img2.save(r"D:\7tan\7tanAI\data\screenshots\searchbox_typed.png")
for t in ocr_enhanced(img2):
    print("  ", t)

# 判断
joined = "".join(t for t in ocr_enhanced(img2))
if "游戏推荐" in joined.replace(" ", ""):
    print("\n✅ 输入成功！按回车执行搜索")
    pyautogui.press("enter")
    time.sleep(3.0)
    img3 = grab_box((351, 149, 968, 645))
    img3.save(r"D:\7tan\7tanAI\data\screenshots\search_result_full.png")
    print("\n=== 搜索结果窗口 OCR ===")
    for t in ocr_enhanced(img3, scale=2):
        print("  ", t)
else:
    print("\n❌ 输入未生效，需要其他方案")
