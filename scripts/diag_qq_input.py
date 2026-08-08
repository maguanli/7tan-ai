# -*- coding: utf-8 -*-
"""用 UIAutomation 检查 QQ 窗口内部的输入框状态，诊断为什么无法输入文字"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import comtypes
import comtypes.client as cc

comtypes.CoInitialize()

user32 = ctypes.windll.user32

# 找到所有 QQ.exe 的顶层窗口
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
kernel32 = ctypes.windll.kernel32

def get_pid(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value

qq_windows = []

@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def enum_cb(hwnd, lparam):
    if not user32.IsWindowVisible(hwnd):
        return True
    pid = get_pid(hwnd)
    # 通过进程路径判断是否为 QQ.exe
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if h:
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            path = buf.value.lower()
            if path.endswith('qq.exe') or 'qqnt' in path:
                length = user32.GetWindowTextLengthW(hwnd)
                tbuf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, tbuf, length + 1)
                qq_windows.append((hwnd, tbuf.value, pid))
        kernel32.CloseHandle(h)
    return True

user32.EnumWindows(enum_cb, 0)

print(f"QQ 顶层窗口数: {len(qq_windows)}\n")
for hwnd, title, pid in qq_windows:
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    print(f"  HWND={hwnd} 标题='{title}' PID={pid} 位置=({rect.left},{rect.top},{rect.right},{rect.bottom})")
print()

# UIA 遍历每个窗口的 Edit 控件
uia = cc.CreateObject('UIAutomationClient.CUIAutomation')
TreeScope_Descendants = 4
UIA_EditControlTypeId = 50004
UIA_DocumentControlTypeId = 50030

EditCondition = uia.CreatePropertyCondition(30003, UIA_EditControlTypeId)  # ControlTypePropertyId=30003

for hwnd, title, pid in qq_windows:
    try:
        elem = uia.ElementFromHandle(hwnd)
        found = elem.FindAll(TreeScope_Descendants, EditCondition)
        print(f"=== 窗口 '{title}' (HWND={hwnd}) 输入框数量: {found.Length} ===")
        for i in range(found.Length):
            e = found.GetElement(i)
            name = e.CurrentName
            aid = e.CurrentAutomationId
            rect = e.CurrentBoundingRectangle
            enabled = e.CurrentIsEnabled
            focused = e.CurrentHasKeyboardFocus
            ctrl_type = e.CurrentControlType
            print(f"  [{i}] Name='{name}' AutomationId='{aid}' "
                  f"Rect=({rect.left},{rect.top},{rect.right},{rect.bottom}) "
                  f"Enabled={enabled} Focused={focused} CtrlType={ctrl_type}")
        print()
    except Exception as ex:
        print(f"=== 窗口 '{title}' 遍历失败: {ex}\n")
