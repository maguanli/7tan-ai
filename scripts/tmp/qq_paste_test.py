# -*- coding: utf-8 -*-
"""剪贴板Ctrl+V测试 + 检查QQ调试端口"""
import asyncio, sys, io, os, tempfile, time, subprocess, ctypes
from ctypes import wintypes
import win32gui, win32con
import pyautogui
import pyperclip
from PIL import ImageGrab, Image

QQ_HWND = 786944

# 1) 检查 QQ 进程是否有调试端口
print('--- netstat QQ ports ---')
r = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk', errors='replace')
qq_pids = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq QQ.exe', '/FO', 'CSV'],
                         capture_output=True, text=True, encoding='gbk', errors='replace').stdout
import re
pids = re.findall(r'"QQ\.exe","(\d+)"', qq_pids)
print('QQ PIDs:', pids)
for line in r.stdout.splitlines():
    for pid in pids:
        if line.strip().endswith(pid) and ('LISTEN' in line or 'ESTABLISHED' in line):
            print(' ', line.strip())
            break

# 2) 剪贴板方案
pyperclip.copy('测试粘贴Abc123')
time.sleep(0.5)
print('clipboard set:', pyperclip.paste())

win32gui.ShowWindow(QQ_HWND, win32con.SW_RESTORE)
win32gui.SetForegroundWindow(QQ_HWND)
time.sleep(1)
print('fg:', win32gui.GetWindowText(win32gui.GetForegroundWindow()))

# 点击输入框
pyautogui.moveTo(1000, 805, duration=0.3)
time.sleep(0.2)
pyautogui.click()
time.sleep(0.8)
# Ctrl+V
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.5)
print('ctrl+v sent')

# OCR 输入框区域
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
