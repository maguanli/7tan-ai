@echo off
chcp 65001 >nul
title 7Tan Web Panel Service
cd /d "%~dp0"
echo ================================================
echo   7Tan Web Panel Service  (background mode)
echo   URL:  http://127.0.0.1:9900/
echo   LAN:  http://本机IP:9900/
echo   No window - service runs hidden in background.
echo   Stop:  taskkill /f /im pythonw.exe
echo ================================================
echo.
wscript "%~dp07TanWebService.vbs"
echo.
echo [OK] Web service started in background (hidden).
echo Open browser:  http://127.0.0.1:9900/
echo You may close this window - service keeps running.
echo.
pause
