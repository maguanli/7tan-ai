# -*- coding: utf-8 -*-
"""修复 rebuild.bat: 增加 PYZ.pyz 校验 + 构建前清理 + 失败日志"""
import re, os

p = r"D:\7tan\7tanAI\dist\rebuild.bat"
with open(p, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 构建命令加 --clean，并记录构建日志
old_build = '"%PYTHON%" -m PyInstaller _build\\build.spec --distpath "%~dp0." --workpath _build\\temp --noconfirm'
new_build = ('"%%PYTHON%%" -m PyInstaller _build\\build.spec --distpath "%%~dp0." --workpath _build\\temp '
             '--noconfirm --clean > build_log.txt 2>&1')
if old_build in content:
    content = content.replace(old_build, new_build)
    print("OK: 构建命令已加 --clean + 日志重定向")
else:
    print("WARN: 未找到原构建命令，跳过")

# 2. 步骤4 验证中增加 PYZ.pyz 检查
old_check = 'if "!PYD_IN!"=="1" ('
new_check = '''if not exist "7tan-editor\\_internal\\PYZ.pyz" (
    echo   [错误] 产物缺少 PYZ.pyz（Python 模块归档），构建不完整！
    echo   常见原因: 杀毒软件拦截构建进程，请将本目录加入杀毒白名单后重试
    echo   构建日志: build_log.txt
    echo.
    echo   [日志末尾] 
    powershell -NoProfile -Command "Get-Content build_log.txt -Tail 15" 2>nul
    pause
    exit /b 1
)
echo   [OK] PYZ.pyz 已生成
if "!PYD_IN!"=="1" ('''
if old_check in content:
    content = content.replace(old_check, new_check)
    print("OK: 已加入 PYZ.pyz 完整性校验")
else:
    print("WARN: 未找到校验锚点，尝试另一种方式")

with open(p, "w", encoding="utf-8") as f:
    f.write(content)
print("已写入:", p)
