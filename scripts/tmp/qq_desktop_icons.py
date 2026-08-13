# -*- coding: utf-8 -*-
import ctypes, sys
from ctypes import wintypes
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32

# 桌面图标 ListView: Progman -> SHELLDLL_DefView -> SysListView32
progman = user32.FindWindowW("Progman", None)
defv = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
if not defv:
    # 兼容 WorkerW
    defv = user32.FindWindowW("SHELLDLL_DefView", None)
lv = user32.FindWindowExW(defv, 0, "SysListView32", None)
print("progman:", progman, "| defview:", defv, "| listview:", lv)

if not lv:
    print("未找到桌面ListView")
    sys.exit(1)

count = user32.SendMessageW(lv, 0x1004, 0, 0)  # LVM_GETITEMCOUNT
print("桌面图标数量:", count)

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

for i in range(count):
    pt = POINT()
    user32.SendMessageW(lv, LVM_GETITEMPOSITION, i, ctypes.byref(pt))
    buf = ctypes.create_unicode_buffer(256)
    item = LVITEM()
    item.pszText = ctypes.cast(buf, wintypes.LPWSTR)
    item.cchTextMax = 256
    user32.SendMessageW(lv, LVM_GETITEMTEXT, i, ctypes.byref(item))
    name = buf.value
    print("idx={} name={!r} pos=({},{})".format(i, name, pt.x, pt.y))
