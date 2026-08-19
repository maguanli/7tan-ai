# -*- coding: utf-8 -*-
"""向7坛游戏社区发送问候（已确认对象）"""
import sys, io, time, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui, pyperclip

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

# 1. 点击左侧列表"7坛游戏社区"确保激活该会话
pyautogui.click(133, 814)
time.sleep(1.8)

# 2. 点击聊天输入框
pyautogui.click(900, 990)
time.sleep(0.8)

# 3. 输入问候语
msg = "大家好！祝7坛游戏社区越来越红火，各位玩得开心！最近有什么好玩的游戏，欢迎推荐分享～🎮"
pyperclip.copy(msg)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.8)

# 4. 截图输入框（发送前留档）
inp = pyautogui.screenshot(region=(400, 900, 1100, 160))
inp.save(r"D:\7tan\7tanAI\data\screenshots\wechat_input.png")
print('输入框截图已保存')

# 5. 回车发送
pyautogui.press('enter')
time.sleep(2.5)

# 6. 全屏截图验证
sent = pyautogui.screenshot()
sent.save(r"D:\7tan\7tanAI\data\screenshots\wechat_sent.png")
print('已发送，截图已保存')

# 7. OCR验证聊天区出现新消息（右下区域 y 850-1030）
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

items = asyncio.run(ocr_file(r"D:\7tan\7tanAI\data\screenshots\wechat_sent.png"))
text = ' '.join(t for _, _, _, _, t in items)
print('===== 画面关键词检查 =====')
found = [k for k in ['红火', '推荐', '分享', '🎮', '玩得开心'] if k in text]
print('命中关键词:', found)
if '红火' in text and ('推荐' in text or '分享' in text):
    print('>> ✅ 发送成功：聊天区已出现问候内容')
else:
    print('>> ⚠️ 未能确认，请人工查看截图 D:\\7tan\\7tanAI\\data\\screenshots\\wechat_sent.png')
