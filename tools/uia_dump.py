# -*- coding: utf-8 -*-
"""用 pywinauto/uiautomation 枚举微信窗口控件树（Qt 可访问性树）"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:\7tan\7tanAI\tools')

try:
    import uiautomation as auto
    print("uiautomation OK", auto.__file__)
    win = auto.ControlFromHandle(657102)
    print("root name:", win.Name, "| type:", win.ControlTypeName)

    def dump(ctrl, depth, max_depth=3):
        if depth > max_depth:
            return
        try:
            name = ctrl.Name or ''
            ctype = ctrl.ControlTypeName or ''
            rect = ''
            try:
                r = ctrl.BoundingRectangle
                rect = f"({r.left},{r.top},{r.right},{r.bottom})"
            except Exception:
                pass
            print("  "*depth + f"{ctype} | {name[:40]!r} | {rect}")
        except Exception as e:
            print("  "*depth + f"ERR {e}")
            return
        try:
            for child in ctrl.GetChildren():
                dump(child, depth+1, max_depth)
        except Exception:
            pass

    dump(win, 0, 2)
except ImportError as e:
    print("uiautomation import fail:", e)
    try:
        from pywinauto import Desktop
        d = Desktop(backend='uia')
        w = d.window(handle=657102)
        print("pywinauto found:", w.window_text())
        w.print_control_identifiers(depth=2, filename=r'D:\7tan\7tanAI\tools\ocr_work\wechat_uia.txt')
        print("saved wechat_uia.txt")
    except Exception as e2:
        print("pywinauto fail:", e2)
