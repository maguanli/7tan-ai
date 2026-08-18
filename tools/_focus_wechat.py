# -*- coding: utf-8 -*-
"""激活微信窗口到前台 + 放大OCR测试"""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import ctypes.wintypes as wt

user32 = ctypes.windll.user32

# 枚举所有可见窗口，找微信
results = []
def enum_cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            results.append((hwnd, title))
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

print("=== 所有可见窗口 ===")
for hwnd, title in results:
    if title.strip():
        print(f"hwnd={hwnd}  title={title}")

# 找微信窗口（标题含 微信/WeChat）
target = None
for hwnd, title in results:
    t = title.lower()
    if ("微信" in title) or ("wechat" in t) or ("weixin" in t):
        target = (hwnd, title)
        break

if target is None:
    print("\n[FAIL] 未找到微信窗口！")
    sys.exit(2)

hwnd, title = target
print(f"\n[OK] 找到微信窗口: hwnd={hwnd} title={title}")

# 激活到前台
user32.ShowWindow(hwnd, 9)  # SW_RESTORE
time.sleep(0.3)
user32.SetForegroundWindow(hwnd)
time.sleep(0.8)

# 获取窗口位置
rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"[OK] 微信窗口位置: left={rect.left} top={rect.top} right={rect.right} bottom={rect.bottom}")
print(f"     大小: {rect.right-rect.left} x {rect.bottom-rect.top}")

# 放大OCR测试：截取微信窗口区域并放大2倍识别
import mss, io
from PIL import Image
with mss.mss() as sct:
    shot = sct.grab({"left": rect.left, "top": rect.top,
                     "width": rect.right-rect.left, "height": rect.bottom-rect.top})
img = Image.frombytes("RGB", shot.size, shot.rgb)
img2 = img.resize((img.width*2, img.height*2), Image.LANCZOS)
img2.save(r"D:\7tan\7tanAI\data\screenshots\wechat_focus_2x.png")

from winrt.windows.media.ocr import OcrEngine
from winrt.windows.globalization import Language
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

engine = OcrEngine.try_create_from_language(Language("zh-CN"))
if engine is None:
    engine = OcrEngine.try_create_from_user_profile_languages()

buf = io.BytesIO(); img2.save(buf, format="PNG"); data = buf.getvalue()
stream = InMemoryRandomAccessStream(); w = DataWriter(stream)
w.write_bytes(data)
if hasattr(w, "store"): w.store()
else: w.store_async().get()
stream.seek(0)
decoder = BitmapDecoder.create_async(stream).get()
bmp = decoder.get_software_bitmap_async().get()
res = engine.recognize_async(bmp).get()

print("\n=== 微信窗口 OCR（放大2倍）===")
lines = [l.text for l in res.lines if l.text.strip()]
for ln in lines:
    print(ln)
print(f"\n[共 {len(lines)} 行文字]")
