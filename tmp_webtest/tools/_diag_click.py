# -*- coding: utf-8 -*-
"""诊断：前台窗口 + 鼠标点击有效性"""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui

user32 = ctypes.windll.user32

def fg_title():
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return hwnd, buf.value

print("=== 当前前台窗口 ===")
hwnd, title = fg_title()
print(f"hwnd={hwnd} title={title}")

WX_HWND = 657102
print(f"\n微信窗口 hwnd={WX_HWND}")

# 尝试多种方式激活微信
for method in range(4):
    if method == 0:
        user32.SetForegroundWindow(WX_HWND)
    elif method == 1:
        user32.ShowWindow(WX_HWND, 9)  # restore
        time.sleep(0.3)
        user32.SetForegroundWindow(WX_HWND)
    elif method == 2:
        # 先点击任务栏微信图标（用 Alt+Tab 序列不可靠，改为直接点任务栏）
        # 用 AttachThreadInput 技巧
        fg = user32.GetForegroundWindow()
        tid_fg = user32.GetWindowThreadProcessId(fg, None)
        tid_me = ctypes.windll.kernel32.GetCurrentThreadId()
        user32.AttachThreadInput(tid_me, tid_fg, True)
        user32.BringWindowToTop(WX_HWND)
        user32.SetForegroundWindow(WX_HWND)
        user32.AttachThreadInput(tid_me, tid_fg, False)
    else:
        # 最小化再恢复
        user32.ShowWindow(WX_HWND, 6)  # minimize
        time.sleep(0.5)
        user32.ShowWindow(WX_HWND, 9)
        time.sleep(0.3)
        user32.SetForegroundWindow(WX_HWND)
    time.sleep(0.6)
    hwnd, title = fg_title()
    print(f"方法{method}: 前台={hwnd} {title}")
    if hwnd == WX_HWND:
        print("  ✅ 微信已在前台")
        break
else:
    print("所有激活方法都失败")

# 现在点击微信窗口内位置，看是否生效
import mss
from PIL import Image

def ocr_quick(box=(351, 149, 968, 645)):
    with mss.mss() as sct:
        shot = sct.grab({"left": box[0], "top": box[1], "width": box[2], "height": box[3]})
    img = Image.frombytes("RGB", shot.size, shot.rgb)
    img.save(r"D:\7tan\7tanAI\data\screenshots\diag_click.png")
    # 用 winrt OCR
    import io
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
    engine = OcrEngine.try_create_from_language(Language("zh-CN"))
    img2 = img.resize((img.width*2, img.height*2), Image.LANCZOS)
    buf = io.BytesIO(); img2.save(buf, format="PNG"); data = buf.getvalue()
    stream = InMemoryRandomAccessStream(); w = DataWriter(stream)
    w.write_bytes(data)
    if hasattr(w, "store"): w.store()
    else: w.store_async().get()
    stream.seek(0)
    decoder = BitmapDecoder.create_async(stream).get()
    bmp = decoder.get_software_bitmap_async().get()
    res = engine.recognize_async(bmp).get()
    return [l.text for l in res.lines if l.text.strip()][:8]

print("\n=== 点击前 OCR ===")
before = ocr_quick()
for t in before: print(" ", t)

# 点击搜索框候选
pyautogui.moveTo(501, 204)
time.sleep(0.3)
print(f"\n鼠标位置: {pyautogui.position()}")
pyautogui.click()
time.sleep(1.0)

hwnd, title = fg_title()
print(f"点击后前台: {hwnd} {title}")
print("\n=== 点击后 OCR ===")
after = ocr_quick()
for t in after: print(" ", t)

print(f"\n变化: {'有' if before != after else '无'}")
