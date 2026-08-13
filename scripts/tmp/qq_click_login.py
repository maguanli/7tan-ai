# -*- coding: utf-8 -*-
"""真实鼠标点击QQ登录按钮，等待后OCR窗口区域确认状态"""
import asyncio, sys, io, os, tempfile, time
import win32gui, win32con
import pyautogui
from PIL import ImageGrab, Image

QQ_HWND = 131828
LOGIN_BTN = (960, 559)

# 确保 QQ 在前台
try:
    win32gui.SetForegroundWindow(QQ_HWND)
except Exception as e:
    print('fg err:', e)
time.sleep(0.8)

# 真实鼠标移动到登录按钮并点击
pyautogui.moveTo(LOGIN_BTN[0], LOGIN_BTN[1], duration=0.4)
time.sleep(0.3)
pyautogui.click()
print('clicked login btn', LOGIN_BTN)

# 等待登录过程
time.sleep(6)

# 重新获取 QQ 窗口矩形并 OCR
try:
    rect = win32gui.GetWindowRect(QQ_HWND)
    print('QQ rect now:', rect)
except Exception as e:
    print('rect err:', e)
    rect = (800, 290, 1120, 750)

async def ocr_rect(rect):
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile
    scale = 1.5
    x0, y0, x1, y1 = rect
    img = ImageGrab.grab(bbox=(x0, y0, x1, y1))
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
    with open(r'D:\7tan\7tanAI\qq_after_login.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('OCR lines:', len(out))

asyncio.run(ocr_rect(rect))
print('DONE')
