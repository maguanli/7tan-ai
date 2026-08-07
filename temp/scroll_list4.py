import pyautogui
import time

# 鼠标移到下拉列表中心 (600,520)，向下滚动列表
pyautogui.moveTo(600, 520)
time.sleep(0.4)
pyautogui.scroll(-500)
time.sleep(0.4)
print("SCROLLED_LIST4")
