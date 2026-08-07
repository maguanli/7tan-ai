import pyautogui
import time

# 把鼠标移到下拉列表上（页面顶部状态下，下拉列表大致在 y=770~1100 区域）
pyautogui.moveTo(650, 900)
time.sleep(0.3)
# 向下滚动滚轮，滚动下拉列表
pyautogui.scroll(-600)
time.sleep(0.5)
print("SCROLLED_DOWN")
