@echo off
chcp 65001 >nul
title 7Tan 网页版控制面板服务
cd /d "%~dp0"

echo ================================================
echo   7Tan 网页版控制面板服务（独立模式）
echo   访问地址：http://127.0.0.1:9900/
echo   局域网访问：http://本机IP:9900/
echo   与桌面版互不影响，桌面版关闭后本服务照常可用
echo   停止：关闭本窗口 或 按 Ctrl+C
echo ================================================
echo.

REM 优先使用虚拟环境 Python
set PYTHON=python
if exist ".venv\Scripts\python.exe" set PYTHON=.venv\Scripts\python.exe

echo 正在启动网页版服务（浏览器访问 http://127.0.0.1:9900/ ）...
echo 按 Ctrl+C 可停止服务
echo.
%PYTHON% main.py --web --host 0.0.0.0 --port 9900

echo.
echo 服务已停止。
pause
