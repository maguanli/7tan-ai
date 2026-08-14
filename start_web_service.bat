@echo off
chcp 65001 >nul
title 7Tan Web Panel Service
cd /d "%~dp0"

echo ================================================
echo   7Tan Web Panel Service (standalone mode)
echo   URL: http://127.0.0.1:9900/
echo   LAN:  http://本机IP:9900/
echo   Works alongside desktop app. Stop: close this window / Ctrl+C
echo ================================================
echo.

set PYTHON=python
if exist ".venv\Scripts\python.exe" set PYTHON=.venv\Scripts\python.exe

echo Starting web service: http://127.0.0.1:9900/
echo Press Ctrl+C to stop
echo.
%PYTHON% main.py --web --host 0.0.0.0 --port 9900

echo.
echo Service stopped.
pause
