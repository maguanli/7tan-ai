# -*- coding: utf-8 -*-
"""探索点击微信搜索框：候选坐标逐个点击 + OCR 验证"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32
HWND = 657102
user32.ShowWindow(HWND, 9); time.sleep(0.2)
user32.SetForegroundWindow(HWND); time.sleep(0.5)

WX = {"left": 351, "top": 149, "w": 968, "h": 645}

from winrt.windows.media.ocr import OcrEngine
from winrt.windows.globalization import Language
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
engine = OcrEngine.try_create_from_language(Language("zh-CN"))
if engine is None:
    engine = OcrEngine.try_create_from_user_profile_languages()

def ocr_region(box):
    with mss.mss() as sct:
        shot = sct.grab({"left": box[0], "top": box[1], "width": box[2], "height": box[3]})
    img = Image.frombytes("RGB", shot.size, shot.rgb)
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

# 候选搜索框位置（相对窗口坐标 → 绝对）
candidates = [
    (150, 55), (150, 70), (250, 55), (80, 50), (200, 60),
    (150, 45), (250, 70), (100, 60), (180, 50), (300, 55),
]

for i, (rx, ry) in enumerate(candidates):
    ax, ay = WX["left"] + rx, WX["top"] + ry
    pyautogui.click(ax, ay)
    time.sleep(0.8)
    texts = ocr_region((WX["left"], WX["top"], WX["w"], 200))
    joined = " | ".join(texts)
    print(f"[{i}] 点击({ax},{ay}) -> OCR顶部: {joined[:120]}")
    # 检测是否出现搜索面板关键词
    if any(k in joined for k in ["搜索", "联系人", "群聊", "文章", "公众号", "小程序", "取消"]):
        print(f"    ★ 疑似搜索面板出现！候选位置=(rx,ry) 绝对=({ax},{ay})")
        # 粘贴输入
        import pyperclip
        pyperclip.copy("游戏推荐")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.6)
        t2 = ocr_region((WX["left"], WX["top"], WX["w"], 150))
        print(f"    输入后OCR: {' | '.join(t2)[:120]}")
        if "游戏推荐" in "".join(t2):
            print("    ✅ 输入成功！按回车搜索")
            pyautogui.press("enter")
            time.sleep(2.0)
            break
        else:
            print("    输入可能未生效，继续尝试")
    time.sleep(0.3)
else:
    print("所有候选位置都未出现搜索面板")
