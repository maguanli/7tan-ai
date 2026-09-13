# -*- coding: utf-8 -*-
"""轮询日志新增行（只打印关键行），观察应用何时/为何关闭"""
import sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

f = Path(r"C:\7tan-test\7tan-editor\logs\app_2026-08-27.log")
keys = ("[Login]", "[Wizard]", "[Onboarding]", "应用已关闭", "closeEvent",
        "ERROR", "WARNING", "Token", "升级", "更新", "update", "重启", "restart")

lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
last = len(lines)
print(f"起始行数: {last}")

for round_i in range(14):
    time.sleep(5)
    lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) > last:
        print(f"\n--- 轮询{round_i+1} 新增 {len(lines)-last} 行 ---")
        for ln in lines[last:]:
            if any(k in ln for k in keys):
                print("  ", ln[:190])
        last = len(lines)
        if any("应用已关闭" in l for l in lines[-5:]):
            print("\n>>> 应用已关闭！最后10行：")
            for ln in lines[-10:]:
                print("   ", ln[:190])
            break
    else:
        print(f"轮询{round_i+1}: 无新增（总{len(lines)}行）")
