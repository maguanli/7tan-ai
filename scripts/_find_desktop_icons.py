# -*- coding: utf-8 -*-
"""枚举桌面图标，定位 QQ 图标坐标（真实双击打开 QQ 用）
v2: 用全局变量 + 正确 argtypes 避免指针问题
"""
import ctypes
import ctypes.wintypes as wt
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LVM_FIRST = 0x1000
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVM_GETITEMW = LVM_FIRST + 75
LVM_GETITEMPOSITION = LVM_FIRST + 16
LVIF_TEXT = 0x0001

user32 = ctypes.windll.user32

# ---- 声明 API 类型 ----
SendMessageW = user32.SendMessageW
SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, ctypes.c_void_p]
SendMessageW.restype = wt.LPARAM

FindWindowW = user32.FindWindowW
FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
FindWindowW.restype = wt.HWND

FindWindowExW = user32.FindWindowExW
FindWindowExW.argtypes = [wt.HWND, wt.HWND, wt.LPCWSTR, wt.LPCWSTR]
FindWindowExW.restype = wt.HWND

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
EnumWindows = user32.EnumWindows
EnumWindows.argtypes = [WNDENUMPROC, wt.LPARAM]
EnumWindows.restype = ctypes.c_bool

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

_global_defview = [0]  # 全局变量存放 DefView 句柄

def _enum_cb(hwnd, lparam):
    dv = FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
    if dv:
        _global_defview[0] = dv
        return False  # 停止枚举
    return True

def find_desktop_listview():
    """找到桌面图标所在的 SysListView32 句柄"""
    # 方式1: Progman -> SHELLDLL_DefView -> SysListView32
    progman = FindWindowW("Progman", None)
    defview = None
    if progman:
        defview = FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
    if not defview:
        # 方式2: 遍历 WorkerW
        _global_defview[0] = 0
        EnumWindows(WNDENUMPROC(_enum_cb), 0)
        defview = _global_defview[0]
    if not defview:
        return None
    return FindWindowExW(defview, 0, "SysListView32", None)

def get_icon_items(listview):
    count = SendMessageW(listview, LVM_GETITEMCOUNT, 0, 0)
    print(f"桌面图标总数: {count}")
    icons = []
    buf = ctypes.create_unicode_buffer(256)
    for i in range(count):
        item = LVITEMW()
        item.mask = LVIF_TEXT
        item.iItem = i
        item.iSubItem = 0
        item.pszText = ctypes.cast(buf, wt.LPWSTR)
        item.cchTextMax = 256
        SendMessageW(listview, LVM_GETITEMW, i, ctypes.byref(item))
        name = buf.value
        pos = wt.POINT()
        SendMessageW(listview, LVM_GETITEMPOSITION, i, ctypes.byref(pos))
        icons.append((name, pos.x, pos.y))
    return icons

def main():
    listview = find_desktop_listview()
    if not listview:
        print("ERROR: 找不到桌面图标列表控件")
        return
    icons = get_icon_items(listview)
    for name, x, y in icons:
        print(f"  [{x},{y}] {name}")
    print("---QQ相关图标---")
    qq_icons = [ic for ic in icons if ic[0] and ("QQ" in ic[0] or "qq" in ic[0].lower())]
    for name, x, y in qq_icons:
        print(f"  [{x},{y}] {name}")
    if not qq_icons:
        print("提示: 未找到 QQ 图标（可能不在桌面，检查开始菜单/任务栏/托盘）")

if __name__ == "__main__":
    main()
