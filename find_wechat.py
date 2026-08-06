import win32gui
import win32con

# 找到微信主窗口
wechat_hwnd = None
def callback(hwnd, extra):
    global wechat_hwnd
    title = win32gui.GetWindowText(hwnd)
    cls = win32gui.GetClassName(hwnd)
    visible = win32gui.IsWindowVisible(hwnd)
    if title or cls:
        # 打印所有包含 WeChat 的窗口
        if 'WeChat' in cls or 'WeChat' in title or 'wechat' in cls.lower():
            print(f"  HWND={hwnd}, Title={repr(title)}, Class={cls}, Visible={visible}")
    # 微信主窗口类名通常是 WeChatMainWndForPC
    if cls == 'WeChatMainWndForPC':
        wechat_hwnd = hwnd
        print(f"\n  >>> Found WeChat Main Window: HWND={hwnd}, Title={repr(title)}, Class={cls}")

win32gui.EnumWindows(callback, None)

if wechat_hwnd:
    print(f"\nWeChat main window found: HWND={wechat_hwnd}")
    # 检查窗口是否可见
    visible = win32gui.IsWindowVisible(wechat_hwnd)
    print(f"Visible: {visible}")
    
    # 如果不可见，尝试显示
    if not visible:
        print("Window is hidden, trying to show it...")
        win32gui.ShowWindow(wechat_hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(wechat_hwnd)
        import time
        time.sleep(1)
        visible = win32gui.IsWindowVisible(wechat_hwnd)
        print(f"After show - Visible: {visible}")
    
    # 获取窗口位置和大小
    rect = win32gui.GetWindowRect(wechat_hwnd)
    print(f"Window rect: {rect}")
else:
    print("\nWeChat main window (WeChatMainWndForPC) not found!")
    print("Trying to find by title...")
    
    # 尝试用 FindWindow
    hwnd = win32gui.FindWindow('WeChatMainWndForPC', None)
    if hwnd:
        print(f"Found via FindWindow: HWND={hwnd}")
    else:
        print("Not found via FindWindow either")
    
    # 列出所有可见窗口
    print("\n--- All visible windows ---")
    def callback2(hwnd, extra):
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        visible = win32gui.IsWindowVisible(hwnd)
        if visible and title:
            print(f"  HWND={hwnd}, Title={repr(title)}, Class={cls}")
    win32gui.EnumWindows(callback2, None)
