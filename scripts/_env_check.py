# -*- coding: utf-8 -*-
"""检查自动化环境依赖"""
import importlib

mods = ["pyautogui", "pyperclip", "mss", "PIL", "ctypes", "win32gui", "win32api", "win32con"]
for m in mods:
    try:
        mod = importlib.import_module(m)
        ver = getattr(mod, "__version__", "?")
        print(f"[OK] {m} {ver}")
    except Exception as e:
        print(f"[FAIL] {m}: {e}")
