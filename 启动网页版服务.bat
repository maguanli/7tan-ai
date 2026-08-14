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
echo   ※ 桌面版运行时不能同时使用（端口冲突）
echo ================================================
echo.

python main.py --web --host 0.0.0.0 --port 9800

echo.
echo 服务已停止。
pause
