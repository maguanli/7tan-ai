# -*- coding: utf-8 -*-
"""PrintWindow 截取指定窗口内容（即使被遮挡也能拿到画面）
用法: python printwin_shot.py <hwnd> <outfile>
"""
import ctypes, sys, os
from ctypes import wintypes

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', ctypes.c_uint32), ('biWidth', ctypes.c_int32),
                ('biHeight', ctypes.c_int32), ('biPlanes', ctypes.c_uint16),
                ('biBitCount', ctypes.c_uint16), ('biCompression', ctypes.c_uint32),
                ('biSizeImage', ctypes.c_uint32), ('biXPelsPerMeter', ctypes.c_int32),
                ('biYPelsPerMeter', ctypes.c_int32), ('biClrUsed', ctypes.c_uint32),
                ('biClrImportant', ctypes.c_uint32)]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER),
                ('bmiColors', ctypes.c_uint32 * 3)]
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

def print_window(hwnd, outfile):
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w <= 0 or h <= 0:
        print(f'❌ 窗口尺寸无效 {w}x{h}')
        return False
    # 创建内存 DC 和位图
    hwndDC = user32.GetWindowDC(hwnd)
    mfcDC = gdi32.CreateCompatibleDC(hwndDC)
    bmp = gdi32.CreateCompatibleBitmap(hwndDC, w, h)
    old = gdi32.SelectObject(mfcDC, bmp)
    # PrintWindow
    PW_RENDERFULLCONTENT = 0x00000002
    result = user32.PrintWindow(hwnd, mfcDC, PW_RENDERFULLCONTENT)
    # 保存为 PNG
    from PIL import Image
    import struct
    bmpinfo = BITMAPINFO()
    bmpinfo.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmpinfo.bmiHeader.biWidth = w
    bmpinfo.bmiHeader.biHeight = -h  # 顶向下
    bmpinfo.bmiHeader.biPlanes = 1
    bmpinfo.bmiHeader.biBitCount = 32
    bmpinfo.bmiHeader.biCompression = 0  # BI_RGB
    buf = ctypes.create_string_buffer(w * h * 4)
    got = gdi32.GetDIBits(mfcDC, bmp, 0, h, buf, ctypes.byref(bmpinfo), 0)
    img = Image.frombuffer('RGBA', (w, h), buf.raw, 'raw', 'BGRA', 0, 1).convert('RGB')
    img.save(outfile)
    # 清理
    gdi32.SelectObject(mfcDC, old)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mfcDC)
    user32.ReleaseDC(hwnd, hwndDC)
    print(f'PrintWindow result={result} 截图 {w}x{h} -> {outfile}')
    return result != 0

if __name__ == '__main__':
    hwnd = int(sys.argv[1])
    out = sys.argv[2]
    ok = print_window(hwnd, out)
    print('OK' if ok else 'FAIL')
