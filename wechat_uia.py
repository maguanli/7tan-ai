# -*- coding: utf-8 -*-
"""用UIAutomation枚举微信窗口控件树，找搜索框"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import uiautomation as auto

# 找微信窗口
win = None
for w in auto.GetRootControl().GetChildren():
    try:
        name = w.Name
        if name and '微信' in name:
            win = w
            print('找到窗口:', repr(name), w.ClassName, w.BoundingRectangle)
            break
    except Exception:
        pass

if not win:
    print('未找到微信窗口')
    sys.exit(1)

# 枚举控件树（前几层）
def walk(ctrl, depth, maxdepth=3):
    if depth > maxdepth:
        return
    try:
        rect = ctrl.BoundingRectangle
        name = ctrl.Name
        ctype = ctrl.ControlTypeName
        print('  ' * depth + f"[{ctype}] name={name!r} rect=({rect.left},{rect.top},{rect.right},{rect.bottom})")
    except Exception as e:
        return
    try:
        for child in ctrl.GetChildren():
            walk(child, depth + 1, maxdepth)
    except Exception:
        pass

print('===== 控件树 =====')
walk(win, 0, 4)
