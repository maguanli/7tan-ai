# -*- coding: utf-8 -*-
"""UIA 枚举 1443834 窗口控件树，定位输入框/发送按钮"""
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

TreeScope_Subtree = 5
all_cond = uia.CreateTrueCondition()

hwnd = 1443834
root = uia.ElementFromHandle(hwnd)
found = root.FindAll(TreeScope_Subtree, all_cond)
print(f"总元素数: {found.Length}")

for i in range(found.Length):
    e = found.GetElement(i)
    name = (e.CurrentName or '').strip()
    ctype = e.CurrentControlType
    r = e.CurrentBoundingRectangle
    if r.right > r.left and r.bottom > r.top:
        print(f"[{i}] type={ctype} name='{name[:50]}' rect=({r.left},{r.top},{r.right},{r.bottom}) "
              f"enabled={e.CurrentIsEnabled} offscreen={e.CurrentIsOffscreen}")
