# -*- coding: utf-8 -*-
"""点击搜索框候选位置 + 粘贴输入 + 回车 + 验证"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui, pyperclip
from PIL import Image
import mss

user32 = ctypes.windll.user32
WX_HWND = 657102
user32.ShowWindow(WX_HWND, 9); time.sleep(0.2)
user32.SetForegroundWindow(WX_HWND); time.sleep(0.4)

def ocr_top():
    with mss.mss() as sct:
        shot = sct.grab({"left": 351, "top": 149, "width": 968, "height": 160})
    img = Image.frombytes("RGB", shot.size, shot.rgb)
    img2 = img.resize((img.width*3, img.height*3), Image.LANCZOS)
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
    return " | ".join(l.text for l in res.lines if l.text.strip())

# 点击多个候选位置，每个都试粘贴输入，看哪个位置输入生效
cands = [(501,204),(601,204),(501,220),(651,204),(431,204),(501,190)]
for ax, ay in cands:
    user32.SetForegroundWindow(WX_HWND); time.sleep(0.2)
    pyautogui.click(ax, ay)
    time.sleep(0.6)
    pyperclip.copy("游戏推荐")
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.6)
    t = ocr_top()
    print(f"点击({ax},{ay}) 输入后顶部OCR: {t[:100]}")
    if "游戏推荐" in t.replace(" ", ""):
        print(f"  ✅ 输入成功于 ({ax},{ay})！回车搜索")
        pyautogui.press("enter")
        time.sleep(2.5)
        # 全窗口 OCR 看搜索结果
        with mss.mss() as sct:
            shot = sct.grab({"left": 351, "top": 149, "width": 968, "height": 645})
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        img.save(r"D:\7tan\7tanAI\data\screenshots\wechat_search_result.png")
        # 识别
        buf = io.BytesIO(); img.save(buf, format="PNG"); data = buf.getvalue()
        stream = InMemoryRandomAccessStream(); w = DataWriter(stream)
        w.write_bytes(data)
        if hasattr(w, "store"): w.store()
        else: w.store_async().get()
        stream.seek(0)
        decoder = BitmapDecoder.create_async(stream).get()
        bmp = decoder.get_software_bitmap_async().get()
        res = engine.recognize_async(bmp).get()
        print("\n=== 搜索结果窗口 OCR ===")
        for l in res.lines:
            if l.text.strip():
                print(" ", l.text)
        break
    time.sleep(0.2)
else:
    print("所有位置输入都未生效")
