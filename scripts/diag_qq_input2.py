# -*- coding: utf-8 -*-
"""用 UIAutomation (comtypes.gen) 检查 QQ 窗口内部的输入框状态"""
import ctypes
import ctypes.wintypes as wt
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import comtypes
comtypes.CoInitialize()

import comtypes.client as cc
cc.GetModule('UIAutomationCore.dll')
from comtypes.gen import UIAutomationClient as UIA

from comtypes import CoCreateInstance, GUID
CLSID_CUIAutomation = GUID('{FF48DBA4-60EF-4201-AA87-54103EEF594E}')
IID_IUIAutomation = GUID('{30CBE57D-D9D0-452A-AB13-7AC5AC4825EE}')
uia = CoCreateInstance(CLSID_CUIAutomation, interface=UIA.IUIAutomation)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

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
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if h:
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            path = buf.value.lower()
            if 'qq' in path and path.endswith('.exe'):
                length = user32.GetWindowTextLengthW(hwnd)
                tbuf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, tbuf, length + 1)
                qq_windows.append((hwnd, tbuf.value, pid))
        kernel32.CloseHandle(h)
    return True

user32.EnumWindows(enum_cb, 0)

# 只保留有实际尺寸的窗口
qq_windows = [w for w in qq_windows if w[0] != 0]

TreeScope_Descendants = 4
EditCond = uia.CreatePropertyCondition(UIA.UIA_ControlTypePropertyId, UIA.UIA_EditControlTypeId)
DocCond = uia.CreatePropertyCondition(UIA.UIA_ControlTypePropertyId, UIA.UIA_DocumentControlTypeId)

for hwnd, title, pid in qq_windows:
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w < 100 or h < 100:
        print(f"[跳过小窗口] HWND={hwnd} '{title}' ({w}x{h})")
        continue
    print(f"\n=== 窗口 '{title}' HWND={hwnd} 尺寸={w}x{h} ===")
    try:
        elem = uia.ElementFromHandle(hwnd)
        edits = elem.FindAll(TreeScope_Descendants, EditCond)
        print(f"  Edit 输入框数量: {edits.Length}")
        for i in range(edits.Length):
            e = edits.GetElement(i)
            r = e.CurrentBoundingRectangle
            print(f"  [Edit {i}] Name='{e.CurrentName}' AId='{e.CurrentAutomationId}' "
                  f"Rect=({r.left},{r.top},{r.right},{r.bottom}) "
                  f"Enabled={e.CurrentIsEnabled} Focused={e.CurrentHasKeyboardFocus} "
                  f"Offscreen={e.CurrentIsOffscreen}")
        docs = elem.FindAll(TreeScope_Descendants, DocCond)
        print(f"  Document 控件数量: {docs.Length}")
        for i in range(docs.Length):
            e = docs.GetElement(i)
            r = e.CurrentBoundingRectangle
            print(f"  [Doc {i}] Name='{e.CurrentName}' AId='{e.CurrentAutomationId}' "
                  f"Rect=({r.left},{r.top},{r.right},{r.bottom}) "
                  f"Enabled={e.CurrentIsEnabled} Focused={e.CurrentHasKeyboardFocus}")
    except Exception as ex:
        print(f"  遍历失败: {ex}")
