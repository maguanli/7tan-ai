# -*- coding: utf-8 -*-
"""枚举所有窗口（含最小化），恢复微信窗口"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes.wintypes as wt
import pyautogui
from PIL import Image
import mss

user32 = ctypes.windll.user32

# 枚举所有窗口（不过滤可见性）
results = []
def enum_cb(hwnd, lparam):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        visible = user32.IsWindowVisible(hwnd)
        results.append((hwnd, buf.value, visible))
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

wx = None
for hwnd, title, visible in results:
    if title.strip() == "微信":
        wx = (hwnd, title, visible)
        print(f"找到微信窗口: hwnd={hwnd} title='{title}' visible={visible}")
        break

if wx is None:
    print("未找到标题为'微信'的窗口，所有窗口如下：")
    for hwnd, title, visible in results:
        if title.strip():
            print(f"  hwnd={hwnd} visible={visible} '{title}'")
    sys.exit(2)

hwnd = wx[0]
# 恢复窗口
user32.ShowWindow(hwnd, 9)  # SW_RESTORE
time.sleep(0.5)
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)
# 再确认
user32.ShowWindow(hwnd, 5)  # SW_SHOW
time.sleep(0.3)
user32.SetForegroundWindow(hwnd)
time.sleep(0.6)

fg = user32.GetForegroundWindow()
print(f"前台窗口: {fg} (期望 {hwnd})")

# 窗口位置
rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"微信窗口位置: ({rect.left},{rect.top})-({rect.right},{rect.bottom})")

time.sleep(0.5)
# 截图确认
with mss.mss() as sct:
    shot = sct.grab({"left": 351, "top": 149, "width": 968, "height": 645})
img = Image.frombytes("RGB", shot.size, shot.rgb)
img.save(r"D:\7tan\7tanAI\data\screenshots\wx_restored.png")

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
