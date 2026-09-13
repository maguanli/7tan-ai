# -*- coding: utf-8 -*-
"""uiautomation 读取微信窗口控件树，找搜索框"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import uiautomation as auto

# 找微信窗口
wx = None
for w in auto.GetRootControl().GetChildren():
    try:
        if w.Name and ("微信" in w.Name or "Weixin" in w.Name):
            wx = w
            break
    except Exception:
        continue

if wx is None:
    print("[FAIL] 找不到微信窗口")
    sys.exit(2)

print(f"[OK] 微信窗口: Name={wx.Name} ClassName={wx.ClassName} ControlType={wx.ControlTypeName}")

# 遍历子控件（前 50 个），找可点击/可编辑控件
def walk(ctl, depth=0, max_depth=3, count=[0]):
    if count[0] > 80:
        return
    try:
        name = ctl.Name
        ctype = ctl.ControlTypeName
        if name or ctype in ("EditControl", "ButtonControl", "ListItemControl", "TabItemControl"):
            print(f"{'  '*depth}{ctype}: '{name}'  class={ctl.ClassName}")
        count[0] += 1
    except Exception:
        return
    if depth < max_depth:
        try:
            for child in ctl.GetChildren():
                walk(child, depth+1, max_depth, count)
        except Exception:
            pass

print("\n=== 微信窗口控件树（前3层）===")
walk(wx)
