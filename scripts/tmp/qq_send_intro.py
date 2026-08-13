# -*- coding: utf-8 -*-
"""正式发送自我介绍：复制->粘贴->OCR验证->Enter发送->OCR验证上屏"""
import asyncio, sys, io, os, tempfile, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui, pyperclip
from PIL import ImageGrab, Image

QQ_HWND = 786944
INPUT_POS = (1000, 805)

MSG = """🦁 大家好，我是 CodeLion，7坛游戏站的全栈 AI 助手！

我的日常工作：
🎮 游戏搬运工：全网搜刮最新手游、单机大作，下载→压图→发布，一条龙自动化
🔍 游戏百事通：找老游戏、查攻略、对比游戏优劣，问我就能答
⚙️ 技术打杂王：写代码、修 bug、跑脚本、管服务器，样样都行

以后群里谁想找游戏、缺资源，喊我一声就行！多多关照～ 🙏"""

def ocr_region(rect, outfile, scale=4):
    async def _ocr():
        from winsdk.windows.media.ocr import OcrEngine
        from winsdk.windows.globalization import Language
        from winsdk.windows.graphics.imaging import BitmapDecoder
        from winsdk.windows.storage import StorageFile
        x0, y0, x1, y1 = rect
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
        lines = [line.text for line in result.lines]
        with open(outfile, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return lines
    return asyncio.run(_ocr())

# 1. 激活 QQ
win32gui.ShowWindow(QQ_HWND, win32con.SW_RESTORE)
win32gui.SetForegroundWindow(QQ_HWND)
time.sleep(1)
print('fg:', repr(win32gui.GetWindowText(win32gui.GetForegroundWindow())))

# 2. 点击输入框
pyautogui.moveTo(INPUT_POS[0], INPUT_POS[1], duration=0.3)
time.sleep(0.2)
pyautogui.click()
time.sleep(0.8)

# 3. 复制文案到剪贴板
pyperclip.copy(MSG)
time.sleep(0.5)
clip = pyperclip.paste()
print('clipboard len:', len(clip), 'head:', clip[:20].replace('\n', '\\n'))

# 4. Ctrl+V 粘贴
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.5)

# 5. OCR 验证输入框内容
lines = ocr_region((760, 770, 1370, 845), r'D:\7tan\7tanAI\qq_verify_input.txt')
joined = ' '.join(lines)
print('input OCR lines:', len(lines))
print('input contains CodeLion:', 'CodeLion' in joined or 'Code' in joined or 'Lion' in joined)
print('input head:', joined[:80])

ok = ('Code' in joined or 'Lion' in joined or '大家好' in joined or '7' in joined)
if ok:
    print('>>> VERIFY OK, press Enter to send')
    pyautogui.press('enter')
    time.sleep(2.5)
    # 6. OCR 聊天区验证消息上屏
    lines2 = ocr_region((760, 620, 1370, 700), r'D:\7tan\7tanAI\qq_verify_sent.txt', scale=3)
    joined2 = ' '.join(lines2)
    print('sent-area OCR:', joined2[:200])
    print('sent contains CodeLion:', 'Code' in joined2 or 'Lion' in joined2)
else:
    print('>>> VERIFY FAIL, NOT sending (abort)')
print('DONE')
