@echo off
chcp 65001 >nul
title 7Tan 网页版控制面板服务
cd /d "%~dp0"

echo ================================================
echo   7Tan 网页版控制面板服务（独立模式）
echo   用途：桌面版关闭后，仍可通过浏览器访问
echo   访问地址：http://127.0.0.1:9800/
echo   局域网访问：http://本机IP:9800/
echo   停止：关闭本窗口 或 按 Ctrl+C
echo ================================================
echo.

REM 优先使用虚拟环境 Python
set PYTHON=python
if exist ".venv\Scripts\python.exe" set PYTHON=.venv\Scripts\python.exe

REM 端口检查：9800 被占用时给出提示
netstat -ano | findstr ":9800" >nul 2>&1
if %errorlevel%==0 (
    echo.
    echo ⚠️  端口 9800 已被占用！
    echo     如果 7Tan 桌面版正在运行，请直接在浏览器打开：
    echo     http://127.0.0.1:9800/
    echo.
    echo     如需独立网页版服务，请先关闭桌面版再运行本脚本。
    echo.
    pause
    exit /b 1
)

echo 正在启动网页版服务（浏览器访问 http://127.0.0.1:9800/ ）...
echo 按 Ctrl+C 可停止服务
echo.
%PYTHON% main.py --web --host 0.0.0.0 --port 9800

echo.
echo 服务已停止。
pause
