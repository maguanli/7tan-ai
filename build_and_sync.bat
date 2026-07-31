@echo off
chcp 65001 >nul
title 7Tan 构建+同步工具
echo ==========================================
echo   7Tan 一键构建 + 同步到 dist
echo ==========================================
echo.

set ROOT=%~dp0
cd /d "%ROOT%"

echo [1/3] 构建 exe...
call "%ROOT%.venv\Scripts\python.exe" -m PyInstaller build.spec --clean
if %ERRORLEVEL% neq 0 (
    echo.
    echo [错误] 构建失败，请检查上方输出
    pause
    exit /b 1
)
echo [1/3] 构建成功
echo.

echo [2/3] 同步源码到 dist\_build\src\...
if not exist "dist\_build\src" mkdir "dist\_build\src"
xcopy src\* dist\_build\src\ /E /Y /Q >nul
if %ERRORLEVEL% neq 0 (
    echo [错误] 源码同步失败
    pause
    exit /b 1
)
echo [2/3] 源码已同步
echo.

echo [3/3] 完成！
echo.
echo   新 exe: dist\7tan-editor\7tan-editor.exe
echo   源码:   dist\_build\src\
echo.
echo   ========================================
echo   免费版/专业版共用 dist，专业版内置构建环境
echo   ========================================
pause
