# -*- coding: utf-8 -*-
"""设置文件对话框文件名并点击打开按钮"""
import sys, time
from pywinauto import Application

HWND = int(sys.argv[1])
PATH = sys.argv[2]

app = Application(backend="uia").connect(handle=HWND)
dlg = app.window(handle=HWND)

edits = dlg.descendants(control_type="Edit")
print("EDIT_COUNT:", len(edits))
for e in edits[:8]:
    try:
        print("EDIT:", repr(e.window_text())[:50], "|", str(e.element_info.name)[:30])
    except Exception:
        pass

target_edit = None
for e in edits:
    try:
        name = str(e.element_info.name)
        if "文件名" in name or "File name" in name or "file name" in name.lower():
            target_edit = e
            break
    except Exception:
        pass
if target_edit is None and edits:
    target_edit = edits[0]

if target_edit:
    try:
        target_edit.set_edit_text(PATH)
        print("SET_EDIT_OK")
    except Exception as e:
        print("SET_EDIT_ERR:", str(e)[:150])
        try:
            target_edit.click_input()
            target_edit.type_keys("^a")
            time.sleep(0.2)
            target_edit.type_keys(PATH)
            print("TYPE_OK")
        except Exception as e2:
            print("TYPE_ERR:", str(e2)[:150])
    time.sleep(0.5)
else:
    print("NO_EDIT")

# 点击打开按钮
try:
    btn = dlg.child_window(title="打开(&O)", control_type="Button")
    btn.click()
    print("BTN_OK")
except Exception as e:
    print("BTN_ERR:", str(e)[:150])
    try:
        dlg.type_keys("{ENTER}")
        print("ENTER_OK")
    except Exception as e2:
        print("ENTER_ERR:", str(e2)[:150])
time.sleep(1)
