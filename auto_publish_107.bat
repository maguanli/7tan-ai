@echo off
chcp 65001 >nul
title 7Tan Editor v1.0.7 一键发布（请先完全退出 7Tan！）
cd /d D:\7tan\7tanAI
echo ============================================
echo   7Tan Editor v1.0.7 自动发布脚本
echo   前提：7Tan 主程序已完全退出（右下角托盘也退出）
echo   否则 pyd 被占用会导致失败！
echo ============================================
echo.
.venv\Scripts\python.exe auto_publish_107.py
echo.
echo 脚本结束，按任意键关闭窗口（可查看上方日志）
pause >nul
