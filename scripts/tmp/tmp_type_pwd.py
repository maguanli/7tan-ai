import sys, time
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    import pyautogui
except ImportError:
    print('NO_PYAUTOGUI')
    sys.exit(2)

# 聚焦密码框 → 全选 → 删除 → 逐键输入 851276
pyautogui.click(1100, 520)
time.sleep(0.4)
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.3)
pyautogui.press('delete')
time.sleep(0.3)
pyautogui.write('851276', interval=0.08)
time.sleep(0.4)
print('PWD_TYPED_OK')
