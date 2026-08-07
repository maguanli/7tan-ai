import pyautogui
import time

# 鼠标移到下拉列表上 (500,900)，向上滚动到列表顶部
pyautogui.moveTo(500, 900)
time.sleep(0.4)
pyautogui.scroll(800)
time.sleep(0.4)
print("SCROLLED_LIST_TOP")
