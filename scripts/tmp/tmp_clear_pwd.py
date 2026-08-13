import sys, time
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import pyautogui

# 1. 聚焦密码框
pyautogui.click(1100, 520)
time.sleep(0.4)

# 2. 光标移到行首
pyautogui.press('home')
time.sleep(0.2)

# 3. 连按 Delete 40 次，确保清空所有字符
for i in range(40):
    pyautogui.press('delete')
    time.sleep(0.02)
time.sleep(0.3)

# 4. 逐键输入 6 位密码
pyautogui.write('851276', interval=0.1)
time.sleep(0.5)
print('CLEAR_AND_TYPE_OK')
