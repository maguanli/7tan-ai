# -*- coding: utf-8 -*-
"""稳健恢复微信窗口到前台"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes.wintypes as wt
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32

def find_wx():
    results = []
    def enum_cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                results.append((hwnd, buf.value))
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    for hwnd, title in results:
        if title.strip() == "微信" or "微信" in title:
            return hwnd, title
    return None, None

hwnd, title = find_wx()
print(f"微信窗口: hwnd={hwnd} title={title}")

# 恢复并置前（多轮）
for i in range(4):
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    time.sleep(0.3)
    # 强制置前
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)  # HWND_TOPMOST + NOMOVE + NOSIZE + SHOWWINDOW
    time.sleep(0.3)
    user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0002)  # HWND_NOTOPMOST
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    fg = user32.GetForegroundWindow()
    if fg == hwnd:
        print(f"[OK] 微信已置前 (第{i+1}轮)")
        break

time.sleep(0.5)

# 截图确认
with mss.mss() as sct:
    shot = sct.grab({"left": 351, "top": 149, "width": 968, "height": 645})
img = Image.frombytes("RGB", shot.size, shot.rgb)
img.save(r"D:\7tan\7tanAI\data\screenshots\wx_restore2.png")

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

print("\n=== 恢复后 OCR ===")
for t in ocr(img, 2)[:25]:
    print(" ", t)
