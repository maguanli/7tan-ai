import pyautogui
import time

# 鼠标移到下拉列表上（列表从 y~800 开始）
pyautogui.moveTo(600, 900)
time.sleep(0.4)
# 向下滚动列表
pyautogui.scroll(-500)
time.sleep(0.4)
print("SCROLLED_LIST3")
