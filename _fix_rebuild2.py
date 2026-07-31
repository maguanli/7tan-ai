# -*- coding: utf-8 -*-
"""修复 rebuild.bat 中 %% 双百分号问题"""
p = r"D:\7tan\7tanAI\dist\rebuild.bat"
with open(p, "r", encoding="utf-8") as f:
    content = f.read()

# 修正双百分号（python replace 时 %% 是字面量，写入文件应为单 %）
fixed = content.replace("%%PYTHON%%", "%PYTHON%").replace("%%~dp0.", "%~dp0.")
if fixed != content:
    with open(p, "w", encoding="utf-8") as f:
        f.write(fixed)
    print("OK: 已修正双百分号")
else:
    print("无需修正")

# 验证关键行
for line in fixed.splitlines():
    if "PyInstaller _build" in line:
        print("构建行:", line.strip())
