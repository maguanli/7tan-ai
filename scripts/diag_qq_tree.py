# -*- coding: utf-8 -*-
"""枚举 QQNT Chromium 渲染树的所有后代元素，定位输入框/群名"""
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
# 收集所有元素
all_cond = uia.CreateTrueCondition()

hwnds = [3672392, 133662]  # 两个聊天窗口

for hwnd in hwnds:
    print(f"\n########## 窗口 HWND={hwnd} ##########")
    try:
        root = uia.ElementFromHandle(hwnd)
        found = root.FindAll(TreeScope_Subtree, all_cond)
        print(f"总元素数: {found.Length}")
        # 打印前 150 个有名称或有意义的元素
        for i in range(found.Length):
            e = found.GetElement(i)
            name = (e.CurrentName or '').strip()
            ctype = e.CurrentControlType
            r = e.CurrentBoundingRectangle
            if (name or ctype in (UIA.UIA_EditControlTypeId, UIA.UIA_ButtonControlTypeId,
                                  UIA.UIA_TextControlTypeId, UIA.UIA_ListItemControlTypeId,
                                  UIA.UIA_TreeItemControlTypeId)) and r.right > r.left:
                if i < 400:
                    print(f"  [{i}] type={ctype} name='{name[:60]}' "
                          f"rect=({r.left},{r.top},{r.right},{r.bottom})")
    except Exception as ex:
        print(f"  失败: {ex}")
