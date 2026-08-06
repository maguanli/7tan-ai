# -*- coding: utf-8 -*-
"""重新枚举微信窗口并最大化"""
import ctypes, sys, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes.wintypes as wt
from PIL import Image
import mss

user32 = ctypes.windll.user32

def enum_all():
    results = []
    def enum_cb(hwnd, lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            results.append((hwnd, buf.value))
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return results

print("=== 所有窗口 ===")
wins = enum_all()
for hwnd, title in wins:
    if title.strip():
        print(f"  hwnd={hwnd} '{title}'")

# 找微信窗口
wx_list = [(h, t) for h, t in wins if t.strip() == "微信" or "Weixin" in t]
print(f"\n微信窗口: {wx_list}")

if not wx_list:
    print("未找到微信窗口！")
    sys.exit(2)

hwnd = wx_list[0][0]

# 先恢复再最大化
user32.ShowWindow(hwnd, 9)  # SW_RESTORE
time.sleep(0.5)
user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
time.sleep(1.0)
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"微信窗口: ({rect.left},{rect.top})-({rect.right},{rect.bottom}) 尺寸 {rect.right-rect.left}x{rect.bottom-rect.top}")
print(f"前台: {user32.GetForegroundWindow()}")

if rect.right - rect.left < 100:
    # 最大化失败，尝试 SetWindowPos 直接设置大小位置
    user32.SetWindowPos(hwnd, 0, 351, 149, 968, 645, 0x0040)
    time.sleep(0.8)
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    print(f"SetWindowPos后: ({rect.left},{rect.top})-({rect.right},{rect.bottom})")

# 截图
left, top = rect.left, rect.top
w, h = rect.right-rect.left, rect.bottom-rect.top
with mss.mss() as sct:
    shot = sct.grab({"left": left, "top": top, "width": w, "height": h})
img = Image.frombytes("RGB", shot.size, shot.rgb)
img.save(r"D:\7tan\7tanAI\data\screenshots\wx_window_now.png")

def ocr(img, scale=2):
    img2 = img.resize((img.width*scale, img.height*scale), Image.LANCZOS)
    buf = io.BytesIO(); img2.save(buf, format="PNG"); data = buf.getvalue()
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
    engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    stream = InMemoryRandomAccessStream(); w2 = DataWriter(stream)
    w2.write_bytes(data)
    if hasattr(w2, "store"): w2.store()
    else: w2.store_async().get()
    stream.seek(0)
    decoder = BitmapDecoder.create_async(stream).get()
    bmp = decoder.get_software_bitmap_async().get()
    res = engine.recognize_async(bmp).get()
    return [l.text for l in res.lines if l.text.strip()]

print("\n=== 微信界面 OCR ===")
for t in ocr(img, 2)[:30]:
    print(" ", t)

# 输出窗口坐标供后续脚本使用
with open(r"D:\7tan\7tanAI\data\wx_window_pos.txt", "w", encoding="utf-8") as f:
    f.write(f"{left},{top},{w},{h}")
print(f"\n窗口坐标已保存: {left},{top},{w},{h}")
