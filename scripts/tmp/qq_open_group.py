# -*- coding: utf-8 -*-
"""点击7723群会话，等待后OCR QQ窗口确认聊天界面"""
import asyncio, sys, io, os, tempfile, time
import win32gui, win32con
import pyautogui
from PIL import ImageGrab, Image

QQ_HWND = 786944
GROUP_POS = (580, 371)

try:
    win32gui.ShowWindow(QQ_HWND, win32con.SW_RESTORE)
    win32gui.SetWindowPos(QQ_HWND, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
    win32gui.SetWindowPos(QQ_HWND, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    win32gui.SetForegroundWindow(QQ_HWND)
except Exception as e:
    print('activate err:', e)
time.sleep(1)

pyautogui.moveTo(GROUP_POS[0], GROUP_POS[1], duration=0.3)
time.sleep(0.2)
pyautogui.click()
print('clicked group', GROUP_POS)

time.sleep(3)

rect = win32gui.GetWindowRect(QQ_HWND)
print('rect:', rect)
x0, y0, x1, y1 = rect

async def ocr():
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile
    scale = 2
    img = ImageGrab.grab(bbox=rect)
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
    with open(r'D:\7tan\7tanAI\qq_group_ocr.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('OCR lines:', len(out))

asyncio.run(ocr())
print('DONE')
