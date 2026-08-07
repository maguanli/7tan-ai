import pyautogui
import time

pyautogui.moveTo(650, 500)
time.sleep(0.3)
pyautogui.scroll(-800)
time.sleep(0.5)
print("SCROLLED_REVIEW")
