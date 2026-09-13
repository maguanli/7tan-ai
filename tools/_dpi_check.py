# -*- coding: utf-8 -*-
import sys, ctypes
sys.path.insert(0, r"D:\7tan\7tanAI\tools")
sys.stdout.reconfigure(encoding="utf-8")
import pyautogui, mss

print("pyautogui.size():", pyautogui.size())

cls = getattr(mss, "MSS", None)
with (cls() if cls else mss.mss()) as sct:
    print("mss monitors:", sct.monitors)

try:
    dpi = ctypes.windll.user32.GetDpiForSystem()
    print("GetDpiForSystem:", dpi)
except Exception as e:
    print("GetDpiForSystem failed:", e)

try:
    scale = ctypes.windll.shcore.GetScaleFactorForDevice(0)
    print("GetScaleFactorForDevice:", scale)
except Exception as e:
    print("GetScaleFactorForDevice failed:", e)
