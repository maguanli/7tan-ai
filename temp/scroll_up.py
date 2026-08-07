import pyautogui
import time

pyautogui.moveTo(650, 400)
time.sleep(0.3)
# 向上滚动回到表单顶部
pyautogui.scroll(800)
time.sleep(0.5)
print("SCROLLED_UP")
