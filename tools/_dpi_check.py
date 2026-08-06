# -*- coding: utf-8 -*-
"""DPI 检测与坐标系统验证"""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pyautogui

# 先设置 DPI aware
try:
    r = ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
    print(f"SetProcessDpiAwareness(2) → {r}")
except Exception as e:
    print("SetProcessDpiAwareness 失败:", e)

# 获取系统 DPI
try:
    dpi = ctypes.windll.user32.GetDpiForSystem()
    print(f"系统 DPI: {dpi} (缩放 {dpi/96*100:.0f}%)")
except Exception as e:
    print("GetDpiForSystem 失败:", e)

# 获取屏幕分辨率（物理）
import mss
with mss.mss() as sct:
    for i, m in enumerate(sct.monitors):
        print(f"显示器{i}: {m}")

# 获取微信窗口位置（此时 DPI aware，应为物理坐标）
user32 = ctypes.windll.user32
hwnd = 657102
import ctypes.wintypes as wt
rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"\n微信窗口(DPI aware后): left={rect.left} top={rect.top} right={rect.right} bottom={rect.bottom}")
print(f"  尺寸: {rect.right-rect.left}x{rect.bottom-rect.top}")

# 鼠标移动到窗口内一点，验证 position
tx, ty = rect.left + 100, rect.top + 100
pyautogui.moveTo(tx, ty)
time.sleep(0.3)
print(f"moveTo({tx},{ty}) → position()={pyautogui.position()}")

# 点击测试：点击微信窗口内的"公众号"文字位置（相对窗口 x=126 y=98 → 物理）
# 相对(126,98) + 窗口左上
cx = rect.left + 126 + 7
cy = rect.top + 98 + 6
pyautogui.click(cx, cy)
time.sleep(0.8)
print(f"click({cx},{cy}) → position()={pyautogui.position()}")

# 全窗口截图对比是否有变化
with mss.mss() as sct:
    shot = sct.grab({"left": rect.left, "top": rect.top,
                     "width": rect.right-rect.left, "height": rect.bottom-rect.top})
from PIL import Image
img = Image.frombytes("RGB", shot.size, shot.rgb)
img.save(r"D:\7tan\7tanAI\data\screenshots\dpi_test_click.png")
print(f"截图已保存，尺寸: {img.size}")
