# -*- coding: utf-8 -*-
"""直接检查 LVITEMW 结构体大小并测试读取桌面图标"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import ctypes
import ctypes.wintypes as wt

LVM_FIRST = 0x1000
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVM_GETITEMW = LVM_FIRST + 75
LVM_GETITEMPOSITION = LVM_FIRST + 16
LVIF_TEXT = 0x0001

user32 = ctypes.windll.user32
SendMessageW = user32.SendMessageW
SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, ctypes.c_void_p]
SendMessageW.restype = wt.LPARAM

FindWindowW = user32.FindWindowW
FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
FindWindowW.restype = wt.HWND
FindWindowExW = user32.FindWindowExW
FindWindowExW.argtypes = [wt.HWND, wt.HWND, wt.LPCWSTR, wt.LPCWSTR]
FindWindowExW.restype = wt.HWND

class LVITEMW(ctypes.Structure):
    _fields_ = [
        ("mask", wt.UINT), ("iItem", ctypes.c_int), ("iSubItem", ctypes.c_int),
        ("state", wt.UINT), ("stateMask", wt.UINT),
        ("pszText", wt.LPWSTR), ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int), ("lParam", wt.LPARAM),
        ("iIndent", ctypes.c_int), ("iGroupId", ctypes.c_int),
        ("cColumns", wt.UINT), ("puColumns", ctypes.POINTER(wt.UINT)),
        ("piColFmt", ctypes.POINTER(ctypes.c_int)), ("iGroup", ctypes.c_int),
    ]

print("LVITEMW size:", ctypes.sizeof(LVITEMW), "(预期 88)")

progman = FindWindowW("Progman", None)
print("Progman:", progman)
defview = None
if progman:
    defview = FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
print("DefView(progman下):", defview)

# 枚举所有顶层窗口，找 SHELLDLL_DefView
found = []
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
def cb(hwnd, lparam):
    dv = FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
    if dv:
        found.append((hwnd, dv))
    return True
user32.EnumWindows(WNDENUMPROC(cb), 0)
print("找到的 DefView:", [(hex(a), hex(b)) for a, b in found])

for owner, dv in found:
    lv = FindWindowExW(dv, 0, "SysListView32", None)
    print(f"DefView={hex(dv)} -> ListView={hex(lv) if lv else None}")
    if lv:
        count = SendMessageW(lv, LVM_GETITEMCOUNT, 0, 0)
        print("  icon count:", count)
        buf = ctypes.create_unicode_buffer(256)
        for i in range(min(count, 10)):
            item = LVITEMW()
            item.mask = LVIF_TEXT
            item.iItem = i
            item.pszText = ctypes.cast(buf, wt.LPWSTR)
            item.cchTextMax = 256
            ret = SendMessageW(lv, LVM_GETITEMW, i, ctypes.byref(item))
            pos = wt.POINT()
            ret2 = SendMessageW(lv, LVM_GETITEMPOSITION, i, ctypes.byref(pos))
            print(f"    item{i}: ret={ret} name={buf.value!r} pos=({pos.x},{pos.y})")
