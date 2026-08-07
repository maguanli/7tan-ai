import pyautogui
import time

# 1) 点击产品下拉打开（当前值 System Center 2012 Endpoint Protection）
pyautogui.click(472, 736)
time.sleep(1.0)

# 2) 按 ↓ 2 次 → Microsoft Defender Antivirus (Windows 11) → (Windows 10)
pyautogui.press('down')
time.sleep(0.2)
pyautogui.press('down')
time.sleep(0.2)

# 3) Enter 确认
pyautogui.press('enter')
time.sleep(0.6)
print("DONE_DOWN2")
