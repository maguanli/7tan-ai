import pyautogui
import time

# 点击下拉打开
pyautogui.click(405, 941)
time.sleep(1.0)

# 按 ↑ 3 次（从 Windows Defender Windows 8 向上 3 项）
pyautogui.press('up')
time.sleep(0.2)
pyautogui.press('up')
time.sleep(0.2)
pyautogui.press('up')
time.sleep(0.2)

# Enter 确认
pyautogui.press('enter')
time.sleep(0.6)
print("DONE_UP3")
