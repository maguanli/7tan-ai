# -*- coding: utf-8 -*-
"""重新打开7坛游戏社区聊天，验证出现内容后再发送 v2"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui, pyperclip
from PIL import Image

SCREENSHOT_DIR = r"D:\7tan\7tanAI\data\screenshots"

def find_wechat():
    wins = []
    def cb(h, out):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if t and ('微信' in t or 'Weixin' in t or 'WeChat' in t):
                out.append((h, t))
    win32gui.EnumWindows(cb, wins)
    return wins

def ocr_file(path, scale=1.5, ox=380, oy=60):
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage import StorageFile

    async def _run():
        file = await StorageFile.get_file_from_path_async(path)
        stream = await file.open_async(0)
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        engine = OcrEngine.try_create_from_language(Language("zh-CN"))
        if engine is None:
            engine = OcrEngine.try_create_from_user_profile_languages()
        result = await engine.recognize_async(bitmap)
        out = []
        for line in result.lines:
            words = line.words
            if words:
                xs = [wd.bounding_rect.x for wd in words]
                ys = [wd.bounding_rect.y for wd in words]
                x2 = max(wd.bounding_rect.x + wd.bounding_rect.width for wd in words)
                y2 = max(wd.bounding_rect.y + wd.bounding_rect.height for wd in words)
                x, y = int(min(xs)), int(min(ys))
                wd, ht = int(x2 - x), int(y2 - y)
            else:
                x = y = wd = ht = 0
            out.append((int(x/scale+ox), int(y/scale+oy), wd, ht, line.text))
        return out
    return asyncio.run(_run())

# 激活微信
wins = find_wechat()
if not wins:
    print('未找到微信窗口'); sys.exit(1)
hwnd = wins[0][0]
win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
time.sleep(0.3)
win32gui.SetForegroundWindow(hwnd)
time.sleep(1.0)

# 点击左侧列表 "7坛游戏" 项
pyautogui.click(126, 812)
time.sleep(3.0)

# 验证右侧聊天是否打开
img = pyautogui.screenshot(region=(380, 60, 1080, 980))
img.save(SCREENSHOT_DIR + r"\wechat_reopen.png")
items = ocr_file(SCREENSHOT_DIR + r"\wechat_reopen.png")
texts = ' '.join(t for _, _, _, _, t in items)
print('===== 右侧区域 OCR =====')
for x, y, w, h, t in items:
    print(f"[{x},{y} {w}x{h}] {t}")

opened = ('早上好' in texts or 'apk' in texts.lower() or '星期二' in texts)
print('>> 聊天窗口状态:', '已打开' if opened else '未打开')
if not opened:
    print('>> 聊天未打开，中止，请人工检查')
    sys.exit(2)

# 聊天已打开 -> 发送
pyautogui.click(900, 985)
time.sleep(1.0)

msg = "大家好！祝7坛游戏社区越来越红火，各位玩得开心！最近有什么好玩的游戏，欢迎推荐分享～🎮"
pyperclip.copy(msg)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.8)

inp = pyautogui.screenshot(region=(400, 900, 1100, 160))
inp.save(SCREENSHOT_DIR + r"\wechat_input2.png")

pyautogui.press('enter')
time.sleep(3.0)

sent = pyautogui.screenshot()
sent.save(SCREENSHOT_DIR + r"\wechat_sent2.png")
print('已发送，验证中...')

items2 = ocr_file(SCREENSHOT_DIR + r"\wechat_sent2.png", 1.3, 0, 0)
text2 = ' '.join(t for _, _, _, _, t in items2)
print('===== 发送后关键词 =====')
print('命中:', [k for k in ['红火', '推荐', '分享', '玩得开心'] if k in text2])
if '红火' in text2 and '分享' in text2:
    print('>> ✅ 发送成功！')
else:
    print('>> ⚠️ 未确认，请查看 wechat_sent2.png 和 wechat_input2.png')
