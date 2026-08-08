# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import uiautomation as auto

# 连接到 QQ 主窗口
win = auto.WindowControl(searchDepth=1, Name='QQ', ClassName='Chrome_WidgetWin_1')
print('尝试查找 QQ 窗口...')
wins = auto.GetRootControl().GetChildren()
qq = None
for w in wins:
    try:
        if 'QQ' in (w.Name or '') and w.ClassName in ('Chrome_WidgetWin_1', 'Qt51512QWindowIcon', ''):
            print('候选窗口:', w.Name, w.ClassName, w.BoundingRectangle)
            if qq is None or w.BoundingRectangle.width() > qq.BoundingRectangle.width():
                qq = w
    except Exception:
        pass

if qq is None:
    print('未找到 QQ 窗口，列出所有顶层窗口:')
    for w in wins:
        try:
            print(' -', repr(w.Name), w.ClassName)
        except Exception:
            pass
    sys.exit(1)

print('使用窗口:', qq.Name, qq.ClassName, qq.BoundingRectangle)

# 遍历找 Edit 控件
print('\n=== Edit 控件 ===')
edits = []
try:
    for ctrl in qq.GetChildren():
        try:
            print('子控件:', ctrl.ControlTypeName, repr(ctrl.Name), ctrl.BoundingRectangle)
        except Exception:
            pass
except Exception as e:
    print('遍历错误:', e)

# 深度遍历所有控件找 Edit
print('\n=== 深度搜索 Edit/输入框 ===')
found_edits = []

def walk(ctrl, depth=0):
    if depth > 6:
        return
    try:
        children = ctrl.GetChildren()
    except Exception:
        return
    for c in children:
        try:
            ct = c.ControlTypeName or ''
            name = c.Name or ''
            rect = c.BoundingRectangle
            if 'Edit' in ct or '输入' in name or '说点什么' in name or '发送' in name:
                print(f'  depth={depth} type={ct} name={repr(name)} rect={rect}')
                found_edits.append((ct, name, rect))
        except Exception:
            pass
        walk(c, depth + 1)

walk(qq)
print(f'\n共找到 {len(found_edits)} 个相关控件')
