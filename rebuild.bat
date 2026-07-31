@echo off
chcp 65001 >nul
title 7Tan 一键构建工具
echo ============================================
echo   7Tan 构建脚本 v18（统一入口）
echo   功能: Git 备份 -> PyInstaller 打包 -> 同步源码
echo ============================================
cd /d "%~dp0"

REM ========== 步骤 1: Git 自动备份 ==========
echo.
echo [1/3] Git 自动备份...
if not exist ".git" (
    echo   - 初始化 git 仓库...
    git init
    git add .gitignore requirements.txt main.py src/ data/prompts/ *.spec rebuild.bat start.bat
    git commit -m "初始提交: 7Tan 源码"
) else (
    git add -A
    git commit -m "auto-save: %date% %time%" >nul 2>&1
)
if %errorlevel% neq 0 (
    echo   (git 提交跳过或无变更)
) else (
    echo   [OK] 已提交
)

REM ========== 步骤 2: 构建 + 同步 ==========
echo.
echo [2/3] PyInstaller 构建 + 同步 dist...
call "%~dp0build_and_sync.bat"

REM ========== 步骤 3: 完成 ==========
echo.
echo [3/3] 完成!
echo ============================================
echo === EXE Info ===
dir "%~dp0dist\7tan-editor\7tan-editor.exe" 2>&1
echo === DONE ===
pause
