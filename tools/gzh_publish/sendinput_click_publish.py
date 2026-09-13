# -*- coding: utf-8 -*-
"""用SendInput底层事件点击弹窗发表文字，避免被窗口拦截"""
import sys, io, time, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import mss
from PIL import Image

user32 = ctypes.windll.user32

def foreground(hwnd):
    user32.ShowWindow(hwnd, 9)
    time.sleep(0.3)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.8)

def send_click(x, y):
    # 移动鼠标
    user32.SetCursorPos(x, y)
    time.sleep(0.3)
    # SendInput 按下/抬起左键
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [('dx', ctypes.c_long), ('dy', ctypes.c_long),
                    ('mouseData', ctypes.c_ulong), ('dwFlags', ctypes.c_ulong),
                    ('time', ctypes.c_ulong), ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong))]
    class INPUT(ctypes.Structure):
        _fields_ = [('type', ctypes.c_ulong), ('mi', MOUSEINPUT)]
    # 需要 union，简化为直接调用 mouse_event
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
    time.sleep(0.1)
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
    print('clicked at', x, y)

def main():
    foreground(132302)
    send_click(455, 456)  # 弹窗"发表"文字中心（全屏坐标）
    time.sleep(4.0)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_sendinput_click.png')
        print('saved after_sendinput_click.png')

if __name__ == '__main__':
    main()
