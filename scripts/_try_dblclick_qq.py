# -*- coding: utf-8 -*-
"""按候选点双击桌面 QQ 图标，直到 QQ.exe 进程启动"""
import sys, io, time, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui

def qq_running():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq QQ.exe", "/FO", "CSV"],
                       capture_output=True, text=True, encoding="gbk", errors="replace")
    return "QQ.exe" in r.stdout

print("QQ 当前运行:", qq_running())

# 候选点击点（基于 OCR: QQ文字在(27,667)，图标在文字上方）
candidates = [
    (36, 620),   # 文字正上方
    (45, 620),
    (36, 630),
    (45, 630),
    (30, 615),
    (50, 625),
    (60, 640),
    (40, 640),
]

for i, (x, y) in enumerate(candidates):
    print(f"\n[{i+1}/{len(candidates)}] 双击 ({x},{y}) ...")
    pyautogui.moveTo(x, y, duration=0.2)
    time.sleep(0.3)
    pyautogui.doubleClick(x, y, interval=0.12)
    time.sleep(2.5)
    if qq_running():
        print(f"  ✅ 成功！QQ.exe 已启动，点击点=({x},{y})")
        break
    else:
        print(f"  QQ 未启动，试下一个点")
else:
    print("\n所有候选点都未启动 QQ")

# 最后再等几秒确认
time.sleep(3)
print("最终 QQ 运行状态:", qq_running())
