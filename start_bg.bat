@echo off
chcp 65001 >nul
REM 用 wmic 创建独立后台进程（不继承调用方句柄，立即返回）
wmic process call create "python D:\7tan\7tanAI\upload_asset.py %1"
echo 已创建独立进程: %1
