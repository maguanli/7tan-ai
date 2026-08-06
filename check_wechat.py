import subprocess
import sys

# 1. 检查 pyautogui
try:
    import pyautogui
    print("OK: pyautogui installed, version:", pyautogui.__version__)
except ImportError:
    print("FAIL: pyautogui not installed")

# 2. 检查 pyperclip
try:
    import pyperclip
    print("OK: pyperclip installed")
except ImportError:
    print("FAIL: pyperclip not installed")

# 3. 检查微信进程
result = subprocess.run(
    ['tasklist', '/FI', 'IMAGENAME eq WeChat.exe'],
    capture_output=True, text=True, encoding='gbk', errors='replace'
)
print("\n--- WeChat Process ---")
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# 4. 查找微信窗口
try:
    import win32gui
    wechat_windows = []
    def callback(hwnd, extra):
        title = win32gui.GetWindowText(hwnd)
        if '微信' in title:
            wechat_windows.append((hwnd, title))
    win32gui.EnumWindows(callback, None)
    if wechat_windows:
        print("Found WeChat windows:")
        for hwnd, title in wechat_windows:
            print(f"  HWND={hwnd}, Title={title}")
    else:
        print("No WeChat window found")
except ImportError:
    print("win32gui not available, trying alternative...")
