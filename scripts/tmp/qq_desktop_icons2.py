# -*- coding: utf-8 -*-
import ctypes, sys
from ctypes import wintypes
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32

# 枚举所有顶层窗口找 SHELLDLL_DefView / SysListView32
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

found_defv = []
found_lv = []

def cb(hwnd, lparam):
    cls = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls, 256)
    c = cls.value
    if c == "SHELLDLL_DefView":
        found_defv.append(int(hwnd))
    if c == "SysListView32":
        found_lv.append(int(hwnd))
    return True

user32.EnumWindows(EnumWindowsProc(cb), 0)
print("SHELLDLL_DefView:", found_defv)
print("SysListView32:", found_lv)

# 在找到的 ListView 中，桌面图标那个通常包含"此电脑"等
LVM_GETITEMCOUNT = 0x1004
LVM_GETITEMPOSITION = 0x1010
LVM_GETITEMTEXT = 0x102D

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class LVITEM(ctypes.Structure):
    _fields_ = [
        ("mask", wintypes.UINT),
        ("iItem", ctypes.c_int),
        ("iSubItem", ctypes.c_int),
        ("state", wintypes.UINT),
        ("stateMask", wintypes.UINT),
        ("pszText", wintypes.LPWSTR),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("lParam", ctypes.c_long),
        ("iIndent", ctypes.c_int),
        ("iGroupId", ctypes.c_int),
        ("cColumns", wintypes.UINT),
        ("puColumns", ctypes.POINTER(ctypes.c_int)),
        ("piColFmt", ctypes.POINTER(ctypes.c_int)),
        ("iGroup", ctypes.c_int),
    ]

for lv in found_lv:
    count = user32.SendMessageW(lv, LVM_GETITEMCOUNT, 0, 0)
    print("ListView", lv, "count:", count)
    if count > 0 and count < 200:
        for i in range(count):
            pt = POINT()
            user32.SendMessageW(lv, LVM_GETITEMPOSITION, i, ctypes.byref(pt))
            buf = ctypes.create_unicode_buffer(256)
            item = LVITEM()
            item.pszText = ctypes.cast(buf, wintypes.LPWSTR)
            item.cchTextMax = 256
            user32.SendMessageW(lv, LVM_GETITEMTEXT, i, ctypes.byref(item))
            name = buf.value
            if name.strip():
                print("  idx={} name={!r} pos=({},{})".format(i, name, pt.x, pt.y))
