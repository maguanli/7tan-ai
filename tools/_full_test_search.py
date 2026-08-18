# -*- coding: utf-8 -*-
"""完整测试：点击搜索框→验证→粘贴→验证"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui, pyperclip
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102
user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
user32.SetForegroundWindow(WX_HWND); time.sleep(0.5)

def grab(box):
    with mss.mss() as sct:
        shot = sct.grab({"left": box[0], "top": box[1], "width": box[2], "height": box[3]})
    return Image.frombytes("RGB", shot.size, shot.rgb)

def diff_pct(a, b):
    pa, pb = a.load(), b.load()
    w, h = a.size
    diff = total = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            total += 1
            if abs(pa[x,y][0]-pb[x,y][0]) + abs(pa[x,y][1]-pb[x,y][1]) + abs(pa[x,y][2]-pb[x,y][2]) > 30:
                diff += 1
    return diff / total * 100 if total else 0

# 搜索框区域（绝对坐标）
BOX = (411, 179, 260, 85)

img0 = grab(BOX)

# 点击搜索框
pyautogui.click(545, 205)
time.sleep(0.8)
pos = pyautogui.position()
print(f"点击后鼠标位置: {pos} (期望 545,205)")
img1 = grab(BOX)
d1 = diff_pct(img0, img1)
print(f"点击后搜索框区域变化: {d1:.2f}%")

# 粘贴
pyperclip.copy("游戏推荐")
time.sleep(0.3)
pyautogui.hotkey("ctrl", "v")
time.sleep(0.8)
img2 = grab(BOX)
d2 = diff_pct(img1, img2)
print(f"粘贴后搜索框区域变化: {d2:.2f}%")
img2.save(r"D:\7tan\7tanAI\data\screenshots\final_search_box.png")

# 全窗口变化
imgf0 = grab((351, 149, 968, 645))
df = diff_pct(imgf0, img2)
print(f"全窗口 vs 搜索框区域(参考): {df:.2f}%")

# 按回车
pyautogui.press("enter")
time.sleep(2.5)
img3 = grab((351, 149, 968, 645))
img3.save(r"D:\7tan\7tanAI\data\screenshots\after_enter_full.png")
d3 = diff_pct(imgf0, img3)
print(f"回车后全窗口变化: {d3:.2f}%")
if d3 > 2:
    print("  → 界面有明显变化！可能搜索成功或弹出面板")

# OCR 全窗口
def ocr_full(img):
    import io as _io
    buf = _io.BytesIO(); img.save(buf, format="PNG"); data = buf.getvalue()
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

print("\n=== 回车后全窗口 OCR ===")
for t in ocr_full(img3)[:20]:
    print(" ", t)
