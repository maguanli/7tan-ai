import pyautogui
import time

# 1) 先滚动页面回到顶部
pyautogui.moveTo(650, 300)
time.sleep(0.3)
pyautogui.scroll(1000)
time.sleep(0.5)

# 2) 点击产品下拉框打开（顶部状态下 y=763）
pyautogui.click(472, 763)
time.sleep(0.8)

# 3) 按 m 键循环跳转 M 开头选项（每次跳下一个）
for i in range(6):
    pyautogui.press('m')
    time.sleep(0.4)

# 4) 回车确认
pyautogui.press('enter')
time.sleep(0.5)
print("DONE_M_JUMP")
