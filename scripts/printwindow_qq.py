# -*- coding: utf-8 -*-
"""PrintWindow 抓取 QQ 窗口自身渲染内容，与屏幕截图对比"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
QQ_HWND = 1443834

user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.5)

rect = wt.RECT()
user32.GetWindowRect(QQ_HWND, ctypes.byref(rect))
w = rect.right - rect.left
h = rect.bottom - rect.top
print(f'窗口: ({rect.left},{rect.top}) {w}x{h}')

# 创建内存 DC 和位图
hdc = user32.GetDC(0)
memdc = gdi32.CreateCompatibleDC(hdc)
hbmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
gdi32.SelectObject(memdc, hbmp)

# 方法1: PrintWindow 基础
user32.PrintWindow(QQ_HWND, memdc, 1)  # PW_CLIENTONLY
bmp1 = ctypes.create_string_buffer(w * h * 4)
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG),
                ('biPlanes', wt.WORD), ('biBitCount', wt.WORD), ('biCompression', wt.DWORD),
                ('biSizeImage', wt.DWORD), ('biXPelsPerMeter', wt.LONG), ('biYPelsPerMeter', wt.LONG),
                ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD)]

bih = BITMAPINFOHEADER()
bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bih.biWidth = w
bih.biHeight = -h  # 自顶向下
bih.biPlanes = 1
bih.biBitCount = 32
bih.biCompression = 0
gdi32.GetDIBits(memdc, hbmp, 0, h, bmp1, ctypes.byref(bih), 0)
img1 = Image.frombuffer('RGB', (w, h), bmp1, 'raw', 'BGRX', 0, 1)
img1.save(r'D:\7tan\7tanAI\scripts\qq_printwindow1.png')

# 方法2: PrintWindow + PW_RENDERFULLCONTENT
gdi32.DeleteObject(hbmp)
hbmp2 = gdi32.CreateCompatibleBitmap(hdc, w, h)
gdi32.SelectObject(memdc, hbmp2)
user32.PrintWindow(QQ_HWND, memdc, 2)  # PW_RENDERFULLCONTENT
bmp2 = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(memdc, hbmp2, 0, h, bmp2, ctypes.byref(bih), 0)
img2 = Image.frombuffer('RGB', (w, h), bmp2, 'raw', 'BGRX', 0, 1)
img2.save(r'D:\7tan\7tanAI\scripts\qq_printwindow2.png')

gdi32.DeleteObject(hbmp2)
gdi32.DeleteDC(memdc)
user32.ReleaseDC(0, hdc)

# 屏幕截图对比
img3 = pyautogui.screenshot(region=(rect.left, rect.top, w, h))
img3.save(r'D:\7tan\7tanAI\scripts\qq_screen_now.png')

# 像素分析：三个图深色比例
for name, im in [('PrintWindow基础', img1), ('PrintWindow全内容', img2), ('屏幕截图', img3)]:
    gray = im.convert('L')
    dark = sum(1 for p in gray.getdata() if p < 128)
    print(f'{name}: 深色 {dark/(gray.width*gray.height)*100:.2f}%')
