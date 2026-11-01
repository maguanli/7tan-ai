# -*- coding: utf-8 -*-
"""量一下更新弹窗装下 747 字说明后的真实尺寸（offscreen，不弹窗）"""
import json
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"D:\7tan\7tanAI")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.ui.update_dialog import UpdateDialog  # noqa: E402

app = QApplication([])

man = json.load(open(r"D:\7tan\7tanAI\website\updates\version.json", encoding="utf-8"))
ent = dict(man["versions"][0])
ent["_current"] = "1.0.22"

dlg = UpdateDialog(ent)
dlg.adjustSize()
hint = dlg.sizeHint()
print("对话框 sizeHint      : %d x %d" % (hint.width(), hint.height()))
print("notes 控件 widget 高度:", dlg._notes.height(), " 建议高度:", dlg._notes.sizeHint().height())
print("notes 字数            :", len(ent["notes"]))
print("屏幕可用高度          :", app.primaryScreen().availableGeometry().height())

# 文字按显示宽度估算行数
fm = dlg._notes.fontMetrics()
avail = max(200, dlg._notes.width() - 24)
lines = 0
for para in ent["notes"].split("\n"):
    w = fm.horizontalAdvance(para)
    lines += max(1, -(-w // avail))
print("估算行数 %d, 行高 %d, 文本高度 ≈ %d" % (lines, fm.height(), lines * fm.height()))

print("\n判定：")
need = hint.height() > app.primaryScreen().availableGeometry().height() - 120
print("  需要滚动区域:", need)
