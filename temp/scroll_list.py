import pyautogui
import time

# 下拉已打开，鼠标移到下拉列表区域并向下滚动
pyautogui.moveTo(650, 250)
time.sleep(0.3)
pyautogui.scroll(-400)
time.sleep(0.5)
print("SCROLLED_LIST")
