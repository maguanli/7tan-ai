# -*- coding: utf-8 -*-
"""检查 Python 位数 + 用 LVM_GETITEMTEXTW 读取桌面图标"""
import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import ctypes
import ctypes.wintypes as wt

print("Python 位数:", struct.calcsize("P") * 8)
print("ctypes sizeof(void*):", ctypes.sizeof(ctypes.c_void_p))

LVM_FIRST = 0x1000
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVM_GETITEMTEXTW = LVM_FIRST + 115  # 0x1073
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

progman = FindWindowW("Progman", None)
defview = FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
lv = FindWindowExW(defview, 0, "SysListView32", None)
print("lv:", hex(lv) if lv else None)
count = SendMessageW(lv, LVM_GETITEMCOUNT, 0, 0)
print("count:", count)

# 方式1: LVM_GETITEMTEXTW
print("\n--- LVM_GETITEMTEXTW ---")
for i in range(min(count, 39)):
    buf = ctypes.create_unicode_buffer(256)
    item = LVITEMW()
    item.mask = LVIF_TEXT
    item.iItem = i
    item.iSubItem = 0
    item.pszText = ctypes.cast(buf, wt.LPWSTR)
    item.cchTextMax = 256
    ret = SendMessageW(lv, LVM_GETITEMTEXTW, i, ctypes.byref(item))
    pos = wt.POINT()
    SendMessageW(lv, LVM_GETITEMPOSITION, i, ctypes.byref(pos))
    print(f"  [{pos.x},{pos.y}] {buf.value!r} (ret={ret})")
