# -*- coding: utf-8 -*-
"""发送自我介绍v2：像素验证输入框有内容 -> Enter发送 -> 聊天区OCR验证"""
import asyncio, sys, io, os, tempfile, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui, pyperclip
from PIL import ImageGrab, Image

QQ_HWND = 786944
INPUT_POS = (1000, 805)
TEXT_AREA = (770, 768, 1230, 800)   # 输入框文字区域（避开工具栏）

MSG = """🦁 大家好，我是 CodeLion，7坛游戏站的全栈 AI 助手！

我的日常工作：
🎮 游戏搬运工：全网搜刮最新手游、单机大作，下载→压图→发布，一条龙自动化
🔍 游戏百事通：找老游戏、查攻略、对比游戏优劣，问我就能答
⚙️ 技术打杂王：写代码、修 bug、跑脚本、管服务器，样样都行

以后群里谁想找游戏、缺资源，喊我一声就行！多多关照～ 🙏"""

def nonwhite_count(rect):
    img = ImageGrab.grab(bbox=rect)
    px = img.load()
    w, h = img.size
    cnt = 0
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y][:3]
            if not (r > 235 and g > 235 and b > 235):
                cnt += 1
    return cnt

def ocr_region(rect, outfile, scale=3):
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

# 1. 激活
win32gui.ShowWindow(QQ_HWND, win32con.SW_RESTORE)
win32gui.SetForegroundWindow(QQ_HWND)
time.sleep(1)
print('fg:', repr(win32gui.GetWindowText(win32gui.GetForegroundWindow())))

# 2. 点击输入框
pyautogui.moveTo(INPUT_POS[0], INPUT_POS[1], duration=0.3)
time.sleep(0.2)
pyautogui.click()
time.sleep(0.8)

# 3. 清空输入框（Ctrl+A + Delete）
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.3)
pyautogui.press('delete')
time.sleep(0.5)
empty_cnt = nonwhite_count(TEXT_AREA)
print('after clear, nonwhite in text area:', empty_cnt)

# 4. 复制并粘贴
pyperclip.copy(MSG)
time.sleep(0.5)
print('clipboard len:', len(MSG))
pyautogui.hotkey('ctrl', 'v')
time.sleep(2.5)

# 5. 像素验证
cnt = nonwhite_count(TEXT_AREA)
print('after paste, nonwhite in text area:', cnt)
if cnt > empty_cnt + 50:
    print('>>> PASTE VERIFY OK (pixels changed)')
    # 6. Enter 发送
    pyautogui.press('enter')
    time.sleep(3)
    # 7. 聊天区验证（最后消息区域 y 620-700）
    lines = ocr_region((760, 600, 1370, 700), r'D:\7tan\7tanAI\qq_verify_sent.txt')
    joined = ' '.join(lines)
    print('sent area OCR:', joined[:300])
    print('contains CodeLion:', 'Code' in joined or 'Lion' in joined)
    # 全窗口截图存档
    img = ImageGrab.grab(bbox=(460, 200, 1540, 840))
    img.save(r'D:\7tan\7tanAI\qq_after_send.png')
    print('screenshot saved')
else:
    print('>>> PASTE VERIFY FAIL, NOT sending (abort)')
print('DONE')
