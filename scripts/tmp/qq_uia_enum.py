# -*- coding: utf-8 -*-
"""UIA枚举QQ窗口控件树，找输入框(Edit/Document)"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import uiautomation as auto

QQ_HWND = 786944
win = auto.ControlFromHandle(QQ_HWND)
print('root:', win.ControlTypeName, repr(win.Name), win.ClassName)

def walk(ctl, depth, max_depth=8):
    try:
        children = ctl.GetChildren()
    except Exception as e:
        return
    for c in children:
        try:
            ct = c.ControlTypeName
            name = c.Name
            cls = c.ClassName
            aid = c.AutomationId
        except Exception:
            continue
        indent = '  ' * depth
        interesting = ('Edit' in ct or 'Document' in ct or 'Content' in ct or
                       '输入' in str(name) or '消息' in str(name) or
                       'Text' in ct and depth > 3)
        if interesting or depth < 3:
            print(f'{indent}{ct} name={name!r} cls={cls!r} aid={aid!r}')
        if depth < max_depth:
            walk(c, depth + 1, max_depth)

walk(win, 1, 6)
print('DONE')
