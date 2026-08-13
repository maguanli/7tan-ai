# -*- coding: utf-8 -*-
"""精确点击输入框中心，SendInput输入，放大OCR输入框区域验证"""
import asyncio, sys, io, os, tempfile, time, ctypes
from ctypes import wintypes
import win32gui, win32con
import pyautogui
from PIL import ImageGrab, Image

QQ_HWND = 786944
INPUT_CENTER = (1000, 805)

def send_unicode(text):
    INPUT_KEYBOARD = 1
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_KEYUP = 0x0002
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT), ("mi", ctypes.c_void_p)]
        _anonymous_ = ("_input",)
        _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]
    def send_key(scan, flags):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki.wVk = 0
        inp.ki.wScan = scan
        inp.ki.dwFlags = flags
        inp.ki.time = 0
        inp.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    for ch in text:
        code = ord(ch)
        send_key(code, KEYEVENTF_UNICODE)
        send_key(code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
        time.sleep(0.03)

win32gui.ShowWindow(QQ_HWND, win32con.SW_RESTORE)
win32gui.SetForegroundWindow(QQ_HWND)
time.sleep(1)
print('fg:', win32gui.GetForegroundWindow(), repr(win32gui.GetWindowText(win32gui.GetForegroundWindow())))

# 双击输入框中心
pyautogui.moveTo(INPUT_CENTER[0], INPUT_CENTER[1], duration=0.3)
time.sleep(0.2)
pyautogui.doubleClick()
time.sleep(1)
print('double clicked input')

# 输入测试
send_unicode('Hello测试中文')
time.sleep(1.5)

# 截图输入框区域放大4x OCR
RECT = (760, 770, 1370, 840)
x0, y0, x1, y1 = RECT
img = ImageGrab.grab(bbox=RECT)
img.save(r'D:\7tan\7tanAI\qq_input_area.png')

async def ocr():
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile
    scale = 4
    w, h = img.size
    img2 = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img2.save(buf, format='PNG')
    fd, tmp = tempfile.mkstemp(suffix='.png')
    with os.fdopen(fd, 'wb') as f:
        f.write(buf.getvalue())
    sf = await StorageFile.get_file_from_path_async(tmp)
    stream = await sf.open_async(0)
    dec = await BitmapDecoder.create_async(stream)
    bitmap = await dec.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_language(Language('zh-Hans-CN'))
    result = await engine.recognize_async(bitmap)
    os.remove(tmp)
    out = []
    for line in result.lines:
        xs = [wd.bounding_rect.x / scale for wd in line.words]
        ys = [wd.bounding_rect.y / scale for wd in line.words]
        ws = [wd.bounding_rect.width / scale for wd in line.words]
        hs = [wd.bounding_rect.height / scale for wd in line.words]
        if not xs:
            continue
        x0l = min(xs); y0l = min(ys)
        x1l = max(x + w for x, w in zip(xs, ws))
        y1l = max(y + h for y, h in zip(ys, hs))
        out.append(f"{line.text}\t{x0l+x0:.0f}\t{y0l+y0:.0f}\t{x1l-x0l:.0f}\t{y1l-y0l:.0f}")
    with open(r'D:\7tan\7tanAI\qq_input_area_ocr.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('OCR lines:', len(out))

asyncio.run(ocr())
print('DONE')
