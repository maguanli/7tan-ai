# -*- coding: utf-8 -*-
"""点击标题框粘贴标题，点击作者框粘贴作者，截屏验证"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, pyperclip
import mss
from PIL import Image

TITLE = '5亿人都在玩的5款手机游戏：第2款治愈到哭，第5款笑出腹肌'
AUTHOR = '7Tan AI'

def click_and_paste(x, y, text, pause=0.6):
    pyautogui.click(x, y)
    time.sleep(pause)
    pyautogui.click(x, y)
    time.sleep(pause)
    pyperclip.copy(text)
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.8)
    print(f'pasted at ({x},{y}): {text[:30]}...')

def main():
    click_and_paste(460, 420, TITLE)
    click_and_paste(410, 462, AUTHOR)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_title_author.png')
        print('saved after_title_author.png')
    print('done')

if __name__ == '__main__':
    main()
