# -*- coding: utf-8 -*-
"""修复：全选标题框重贴标题，再点作者框贴作者"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, pyperclip
import mss
from PIL import Image

TITLE = '5亿人都在玩的5款手机游戏：第2款治愈到哭，第5款笑出腹肌'
AUTHOR = '7Tan AI'

def main():
    # 1. 点击标题框，全选，粘贴正确标题
    pyautogui.click(460, 420)
    time.sleep(0.6)
    pyautogui.click(460, 420)
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.3)
    pyperclip.copy(TITLE)
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.8)
    print('title re-pasted')
    # 2. 点击作者框（placeholder 在 y=483，输入框中心约 y=495）
    pyautogui.click(410, 495)
    time.sleep(0.6)
    pyautogui.click(410, 495)
    time.sleep(0.4)
    pyperclip.copy(AUTHOR)
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.8)
    print('author pasted')
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_fix_title_author.png')
        print('saved')

if __name__ == '__main__':
    main()
