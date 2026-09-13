@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===  设置 7Tan 服务器发布密码  ===
echo.
python "%~dp0scripts\set_deploy_password.py"
echo.
pause
