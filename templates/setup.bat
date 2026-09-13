@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 7Tan - 环境准备

echo ================================================
echo   7Tan 源码构建 - 环境准备
echo ================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] 未检测到 Python，请先安装 Python 3.12:
    echo         https://www.python.org/downloads/
    echo         安装时务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/3] 创建虚拟环境 .venv ...
if exist ".venv\Scripts\python.exe" (
    echo   [OK] .venv 已存在，跳过创建
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo   [OK] .venv 创建完成
)

echo [2/3] 升级 pip 并安装依赖（约 2-5 分钟）...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] 依赖安装失败，请检查网络后重试
    pause
    exit /b 1
)
echo   [OK] 依赖安装完成

echo [3/3] 验证 PyInstaller ...
".venv\Scripts\python.exe" -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] PyInstaller 不可用
    pause
    exit /b 1
)
echo   [OK] PyInstaller 就绪

echo.
echo ================================================
echo   [OK] 环境就绪！接下来运行:
echo       build.bat
echo   即可构建 exe（约 10-15 分钟，不含打包）
echo ================================================
pause
