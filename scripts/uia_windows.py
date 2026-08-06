# -*- coding: utf-8 -*-
"""枚举 UIA 顶层窗口"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import uiautomation as auto

root = auto.GetRootControl()
for win in root.GetChildren():
    try:
        name = win.Name
        cls = win.ClassName
        ctype = win.ControlTypeName
        print(f'[{ctype}] name={name!r} class={cls!r} rect={win.BoundingRectangle}')
    except Exception as e:
        print(f'[ERR] {e}')
print('===== END =====')
