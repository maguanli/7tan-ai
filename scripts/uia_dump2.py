# -*- coding: utf-8 -*-
"""用 UIA 读取微信窗口控件树（mmui::MainWindow）"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import uiautomation as auto

win = auto.WindowControl(searchDepth=1, ClassName='mmui::MainWindow')
if not win.Exists(2):
    print('ERR: 未找到微信窗口')
    sys.exit(1)
print(f'找到窗口: {win.Name!r} class={win.ClassName} rect={win.BoundingRectangle}')

def dump(control, depth=0, max_depth=5):
    if depth > max_depth:
        return
    try:
        name = control.Name
        ctype = control.ControlTypeName
        rect = control.BoundingRectangle
        print(f'{"  " * depth}[{ctype}] name={name!r} rect=({rect.left},{rect.top},{rect.right},{rect.bottom})')
    except Exception as e:
        print(f'{"  " * depth}[ERR] {e}')
        return
    try:
        for child in control.GetChildren():
            dump(child, depth + 1, max_depth)
    except Exception:
        pass

dump(win, 0, 5)
print('===== END =====')
