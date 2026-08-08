# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pywinauto import Desktop, Application

# 方法1: Desktop 遍历所有窗口
try:
    desktop = Desktop(backend='uia')
    wins = desktop.windows()
    print('=== 所有窗口 ===')
    for w in wins:
        try:
            print(f'  {w.window_text()!r} class={w.class_name()} handle={w.handle}')
        except Exception:
            pass
except Exception as e:
    print('Desktop 遍历失败:', e)

# 方法2: 连接到 QQ 主窗口
print('\n=== 连接 QQ 主窗口 (hwnd=657662) ===')
try:
    app = Application(backend='uia').connect(handle=657662)
    win = app.window(handle=657662)
    print('窗口:', win.window_text())
    # 深度遍历找 Edit
    def walk(ctrl, depth=0):
        if depth > 10:
            return
        try:
            children = ctrl.children()
        except Exception:
            return
        for c in children:
            try:
                ctype = c.element_info.control_type
                cname = c.window_text() or ''
                crect = c.rectangle()
                if ctype in ('Edit', 'Document', 'Pane') or '输入' in cname or '发送' in cname:
                    print(f'  {"  "*depth}[{ctype}] {cname!r} rect={crect}')
            except Exception:
                pass
            walk(c, depth + 1)
    walk(win)
except Exception as e:
    print('连接失败:', e)
    import traceback
    traceback.print_exc()
