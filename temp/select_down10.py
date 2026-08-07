import pyautogui
import time

# 1) 回页面顶部
pyautogui.moveTo(650, 300)
time.sleep(0.3)
pyautogui.scroll(1500)
time.sleep(0.5)

# 2) 点击产品下拉打开
pyautogui.click(472, 762)
time.sleep(1.0)

# 3) 按 ↓ 键 10 次（从第一项往下移动到目标附近）
for i in range(10):
    pyautogui.press('down')
    time.sleep(0.15)

# 4) Enter 确认
pyautogui.press('enter')
time.sleep(0.6)
print("DONE_DOWN10")
