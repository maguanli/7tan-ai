import sys
try:
    import pyautogui
    print("PYAUTOGUI_OK", pyautogui.size())
except Exception as e:
    print("PYAUTOGUI_FAIL", e)
