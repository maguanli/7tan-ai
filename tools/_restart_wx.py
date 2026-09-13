# -*- coding: utf-8 -*-
"""重启微信：杀进程→启动→等待窗口→激活"""
import sys, subprocess, time, os, ctypes
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import ctypes.wintypes as wt

user32 = ctypes.windll.user32

# 1. 杀掉微信进程
print("[1] 结束微信进程...")
r = subprocess.run(["taskkill", "/IM", "Weixin.exe", "/F", "/T"],
                   capture_output=True, text=True, encoding="gbk", errors="replace")
print("   ", r.stdout.strip() or r.stderr.strip())
time.sleep(2)

# 2. 确认进程已退出
r2 = subprocess.run(["tasklist"], capture_output=True, text=True, encoding="gbk", errors="replace")
alive = [l for l in r2.stdout.splitlines() if "Weixin" in l]
print(f"   剩余微信进程: {len(alive)}")

# 3. 启动微信
WX_EXE = r"C:\Program Files\Tencent\Weixin\Weixin.exe"
print(f"[2] 启动微信: {WX_EXE}")
if not os.path.exists(WX_EXE):
    print("   微信路径不存在！")
    sys.exit(2)
subprocess.Popen([WX_EXE], cwd=os.path.dirname(WX_EXE))

# 4. 等待窗口出现（最多 60 秒）
print("[3] 等待微信窗口出现...")
def find_wx():
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
    for hwnd, title in results:
        if title.strip() == "微信":
            return hwnd
    return None

hwnd = None
for i in range(60):
    hwnd = find_wx()
    if hwnd:
        print(f"   ✅ 微信窗口出现: hwnd={hwnd} (等待{i*2}秒)")
        break
    time.sleep(2)

if hwnd is None:
    print("   ❌ 60秒内微信窗口未出现")
    sys.exit(2)

# 5. 激活窗口
time.sleep(2)
user32.ShowWindow(hwnd, 9); time.sleep(0.3)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"微信窗口位置: ({rect.left},{rect.top})-({rect.right},{rect.bottom})")
print(f"前台窗口: {user32.GetForegroundWindow()}")

# 6. 截图确认
import mss
from PIL import Image
import io
with mss.mss() as sct:
    shot = sct.grab({"left": rect.left, "top": rect.top,
                     "width": rect.right-rect.left, "height": rect.bottom-rect.top})
img = Image.frombytes("RGB", shot.size, shot.rgb)
img.save(r"D:\7tan\7tanAI\data\screenshots\wx_restarted.png")

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

print("\n=== 重启后微信界面 OCR ===")
for t in ocr(img, 2)[:25]:
    print(" ", t)
