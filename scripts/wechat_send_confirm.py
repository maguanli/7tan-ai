# -*- coding: utf-8 -*-
"""带确认的发送：OCR顶部群名 -> 确认后发送问候 -> 验证"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui, pyperclip
from PIL import Image

def find_wechat():
    wins = []
    def cb(h, out):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if t and ('微信' in t or 'Weixin' in t or 'WeChat' in t):
                out.append((h, t))
    win32gui.EnumWindows(cb, wins)
    return wins

wins = find_wechat()
if not wins:
    print('未找到微信窗口'); sys.exit(1)
hwnd = wins[0][0]
win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
time.sleep(0.3)
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.8)

# 截图顶部标题区 (x 400-1500, y 60-180) 放大2x
img = pyautogui.screenshot(region=(400, 60, 1100, 120))
img = img.resize((2200, 240), Image.LANCZOS)
img.save(r"D:\7tan\7tanAI\data\screenshots\wechat_head.png")

from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage import StorageFile

async def ocr_file(path: str):
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
        out.append((x, y, wd, ht, line.text))
    return out

items = asyncio.run(ocr_file(r"D:\7tan\7tanAI\data\screenshots\wechat_head.png"))
head_text = ' '.join(t for _, _, _, _, t in items)
print('顶部标题 OCR:', head_text)

# 确认：标题包含 7坛/游戏/社区 任一
confirm = ('7坛' in head_text or '游戏' in head_text or '社区' in head_text or '7 坛' in head_text)
print('确认结果:', '通过 - 是7坛游戏社区聊天窗口' if confirm else '未确认 - 中止发送！')

if not confirm:
    print('!! 未确认聊天对象，不发送，请人工检查 !!')
    sys.exit(2)

# ===== 确认通过，发送 =====
# 点击输入框
pyautogui.click(900, 990)
time.sleep(0.8)

msg = "大家好！祝7坛游戏社区越来越红火，各位玩得开心！最近有什么好玩的游戏，欢迎推荐分享～🎮"
pyperclip.copy(msg)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.8)

# 截图输入框确认
inp = pyautogui.screenshot(region=(400, 900, 1000, 150))
inp.save(r"D:\7tan\7tanAI\data\screenshots\wechat_input.png")

# 回车发送
pyautogui.press('enter')
time.sleep(2.5)

# 全屏截图验证
sent = pyautogui.screenshot()
sent.save(r"D:\7tan\7tanAI\data\screenshots\wechat_sent.png")
print('已回车发送，等待验证...')

# OCR 聊天区确认消息出现
items2 = asyncio.run(ocr_file(r"D:\7tan\7tanAI\data\screenshots\wechat_sent.png"))
sent_text = ' '.join(t for _, _, _, _, t in items2)
print('发送后画面关键词检查:')
if '红火' in sent_text and '推荐分享' in sent_text:
    print('>> 发送成功：聊天区出现问候内容')
else:
    print('>> 未确认消息出现，请查看截图 wechat_sent.png')
