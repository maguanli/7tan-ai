# -*- coding: utf-8 -*-
import sys
mods = ["pyautogui", "mss", "pyperclip", "PIL", "pytesseract"]
for m in mods:
    try:
        mod = __import__(m)
        ver = getattr(mod, "__version__", "?")
        print(f"[OK] {m} {ver}")
    except Exception as e:
        print(f"[FAIL] {m}: {e}")

try:
    import winrt
    print("[OK] winrt")
except Exception:
    try:
        import winsdk
        print("[OK] winsdk")
    except Exception as e:
        print("[FAIL] winrt/winsdk:", e)
