@echo off
chcp 65001 >nul
title 7Tan 服务器密码设置
cd /d "%~dp0"
echo.
echo ============================================================
echo   设置 7Tan 服务器发布密码
echo ============================================================
echo.
echo   稍后会弹出一个【图形窗口】输入密码。
echo   如果窗口没有出现，请查看任务栏（可能被控制台挡住）。
echo.
set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% "%~dp0scripts\set_deploy_password.py" %*
echo.
pause
