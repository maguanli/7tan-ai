@echo off
chcp 65001 >nul
title 7Tan 本地模型停止器
echo 正在停止 7Tan 本地模型 (llama-server) ...
taskkill /F /IM llama-server.exe >nul 2>&1
if %errorlevel%==0 (
    echo [OK] 已停止。
) else (
    echo [提示] 没有检测到运行中的 llama-server。
)
pause
