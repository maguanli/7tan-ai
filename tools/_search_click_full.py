# -*- coding: utf-8 -*-
"""点击搜索框 → 全窗口 diff（面板可能在别处弹出）"""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui, pyperclip
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102
user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
user32.SetForegroundWindow(WX_HWND); time.sleep(0.5)

def grab():
    with mss.mss() as sct:
        shot = sct.grab({"left": 351, "top": 149, "width": 968, "height": 645})
    return Image.frombytes("RGB", shot.size, shot.rgb)

def diff_map(a, b):
    """返回变化区域的范围 (x0,y0,x1,y1) 和百分比"""
    pa, pb = a.load(), b.load()
    w, h = a.size
    minx, miny, maxx, maxy = w, h, -1, -1
    diff = total = 0
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            total += 1
            if abs(pa[x,y][0]-pb[x,y][0]) + abs(pa[x,y][1]-pb[x,y][1]) + abs(pa[x,y][2]-pb[x,y][2]) > 30:
                diff += 1
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
    return diff/total*100, (minx, miny, maxx, maxy)

img0 = grab()

# 点击搜索框候选（白色矩形中心）
pyautogui.click(545, 205)
time.sleep(1.2)
img1 = grab()
d1, r1 = diff_map(img0, img1)
print(f"点击搜索框(545,205) → 全窗口变化 {d1:.2f}%  区域={r1}")
img1.save(r"D:\7tan\7tanAI\data\screenshots\search_click_full.png")

# 如果点击生效（弹面板），OCR 全窗口
if d1 > 0.5:
    import io
    def ocr(img):
        img2 = img.resize((img.width*2, img.height*2), Image.LANCZOS)
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
    print("\n=== 点击后全窗口 OCR ===")
    for t in ocr(img1)[:25]:
        print(" ", t)
else:
    print("\n点击无变化，尝试输入后回车验证……")
    pyperclip.copy("游戏推荐")
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(2.5)
    img2 = grab()
    d2, r2 = diff_map(img0, img2)
    print(f"粘贴+回车后全窗口变化 {d2:.2f}%  区域={r2}")
    img2.save(r"D:\7tan\7tanAI\data\screenshots\search_enter_full.png")
