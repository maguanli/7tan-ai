import pyautogui
import time

# 1) 点击产品下拉打开（当前布局 y=376）
pyautogui.click(472, 376)
time.sleep(0.8)

# 2) 输入前缀搜索 "microsoft de" → 高亮 Microsoft Defender...
pyautogui.typewrite('microsoft de', interval=0.12)
time.sleep(0.5)

# 3) 回车确认
pyautogui.press('enter')
time.sleep(0.5)
print("DONE_TYPED_SEARCH")
