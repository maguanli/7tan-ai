import subprocess
import sys

# 检查微信进程 - 用更兼容的方式
result = subprocess.run(
    'tasklist | findstr WeChat',
    shell=True,
    capture_output=True, text=True, encoding='gbk', errors='replace'
)
print("--- WeChat Process ---")
if result.stdout and 'WeChat' in result.stdout:
    print("WeChat is running!")
    print(result.stdout)
else:
    print("WeChat process not found in tasklist")
    print("stdout:", repr(result.stdout))
    print("stderr:", repr(result.stderr))

# 查找微信窗口
try:
    import win32gui
    wechat_windows = []
    def callback(hwnd, extra):
        title = win32gui.GetWindowText(hwnd)
        if title and ('微信' in title or 'WeChat' in title):
            wechat_windows.append((hwnd, title, win32gui.IsWindowVisible(hwnd)))
    win32gui.EnumWindows(callback, None)
    print("\n--- WeChat Windows ---")
    if wechat_windows:
        for hwnd, title, visible in wechat_windows:
            print(f"  HWND={hwnd}, Title={title}, Visible={visible}")
    else:
        print("No WeChat window found")
except Exception as e:
    print(f"win32gui error: {e}")

# 检查屏幕尺寸
try:
    import pyautogui
    size = pyautogui.size()
    print(f"\nScreen size: {size}")
except Exception as e:
    print(f"Screen size error: {e}")
