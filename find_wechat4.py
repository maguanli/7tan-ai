import win32gui
import win32con
import time

# 新版微信改名为 Weixin，窗口类名可能不同
# 尝试多种方式查找微信窗口

print("=== 查找微信窗口 ===\n")

# 方法1: 枚举所有窗口，查找包含微信/WeChat/Weixin 的
all_windows = []
def callback(hwnd, extra):
    title = win32gui.GetWindowText(hwnd)
    cls = win32gui.GetClassName(hwnd)
    visible = win32gui.IsWindowVisible(hwnd)
    all_windows.append((hwnd, title, cls, visible))
    
    # 检查各种可能的微信窗口标识
    title_str = title if title else ""
    cls_str = cls if cls else ""
    combined = (title_str + cls_str).lower()
    
    if any(kw in combined for kw in ['wechat', 'weixin', '微信']):
        print(f"  [匹配] HWND={hwnd}, Title={repr(title)}, Class={cls}, Visible={visible}")

win32gui.EnumWindows(callback, None)

# 方法2: 尝试常见的微信窗口类名
print("\n=== 尝试 FindWindow ===")
class_names = [
    'WeChatMainWndForPC',
    'WeixinMainWndForPC',
    'WeUIMainWndForPC',
    'ChatWnd',
    'WeChatLoginWndForPC',
    'WeixinLoginWndForPC',
]
for cls_name in class_names:
    hwnd = win32gui.FindWindow(cls_name, None)
    if hwnd:
        title = win32gui.GetWindowText(hwnd)
        print(f"  Found: Class={cls_name}, HWND={hwnd}, Title={repr(title)}")

# 方法3: 列出所有可见且有标题的窗口
print("\n=== 所有可见窗口 ===")
for hwnd, title, cls, visible in all_windows:
    if visible and title:
        print(f"  HWND={hwnd}, Title={repr(title)}, Class={cls}")
