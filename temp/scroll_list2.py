import pyautogui
import time

# 下拉已打开：鼠标移到列表中心 (500,300)，向下滚动
pyautogui.moveTo(500, 300)
time.sleep(0.4)
pyautogui.scroll(-500)
time.sleep(0.4)
print("SCROLLED")
