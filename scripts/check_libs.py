# -*- coding: utf-8 -*-
"""检查 UI 自动化相关库是否可用"""
import importlib.util
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mods = ['uiautomation', 'pywinauto', 'pyautogui', 'PIL', 'pynput',
        'comtypes', 'mss', 'pyperclip', 'psutil']
for m in mods:
    spec = importlib.util.find_spec(m)
    print(f"{m}: {'OK' if spec else 'MISSING'}")
