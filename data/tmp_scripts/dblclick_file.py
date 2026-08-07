# -*- coding: utf-8 -*-
"""双击文件对话框中的目标文件"""
import sys, time
from pywinauto import Application

HWND = int(sys.argv[1])
FNAME = sys.argv[2]

app = Application(backend="uia").connect(handle=HWND)
dlg = app.window(handle=HWND)
items = dlg.descendants(control_type="ListItem")
names = [it.window_text() for it in items]
print("ITEMS:", names[:12])
target = None
for it in items:
    n = it.window_text()
    if n.strip() == FNAME:
        target = it
        break
if target is None:
    for it in items:
        n = it.window_text()
        if "7tan-editor" in n and n.strip().endswith(".zip"):
            target = it
            break
if target:
    target.double_click_input()
    print("DOUBLE_CLICKED")
    time.sleep(2)
else:
    print("NOT_FOUND")
