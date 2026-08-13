# -*- coding: utf-8 -*-
"""点击QQ输入框，SendInput Unicode输入测试文字，OCR验证上屏"""
import asyncio, sys, io, os, tempfile, time, ctypes
from ctypes import wintypes
import win32gui, win32con
import pyautogui
from PIL import ImageGrab, Image

QQ_HWND = 786944
INPUT_POS = (1000, 800)   # 输入框位置（聊天区底部）

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
        time.sleep(0.02)
    print('sent', len(text), 'chars')

# 激活QQ
try:
    win32gui.ShowWindow(QQ_HWND, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(QQ_HWND)
except Exception as e:
    print('activate err:', e)
time.sleep(1)

# 点击输入框
pyautogui.moveTo(INPUT_POS[0], INPUT_POS[1], duration=0.3)
time.sleep(0.2)
pyautogui.click()
time.sleep(0.8)
print('clicked input box', INPUT_POS)

# 输入测试文字
send_unicode('你好123')

time.sleep(1.5)

# OCR 输入框区域验证
RECT = (700, 760, 1540, 840)
x0, y0, x1, y1 = RECT

async def ocr():
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile
    scale = 3
    img = ImageGrab.grab(bbox=RECT)
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
    with open(r'D:\7tan\7tanAI\qq_input_test.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('OCR lines:', len(out))

asyncio.run(ocr())
print('DONE')
