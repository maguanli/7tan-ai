# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
for m in ('win32clipboard', 'winsdk', 'winrt', 'pyperclip', 'pyautogui'):
    try:
        __import__(m)
        print('OK  ', m)
    except Exception as e:
        print('MISS', m, '->', e)
