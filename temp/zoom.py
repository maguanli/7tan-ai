import pyautogui
import time

# 放大 Chrome 页面两次（150%）
pyautogui.hotkey('ctrl', '=')
time.sleep(0.5)
pyautogui.hotkey('ctrl', '=')
time.sleep(0.5)
print("ZOOMED")
