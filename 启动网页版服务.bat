@echo off
chcp 65001 >nul
title 7Tan 网页版控制面板
cd /d "%~dp0"

echo ================================================
echo   7Tan 网页版控制面板
echo   访问地址: http://127.0.0.1:9900/
echo ================================================
echo.

REM 优先使用虚拟环境 Python
set PYTHON=pythonw
if exist ".venv\Scripts\pythonw.exe" set PYTHON=.venv\Scripts\pythonw.exe

REM 自动配置开机自启(幂等: 已配置自动跳过, 无需用户操作)
"%PYTHON%" tools\web_autostart.py --install >nul 2>&1
echo [OK] 开机自启已配置: 以后电脑开机自动运行网页版服务, 随时可直接访问 http://127.0.0.1:9900/
echo.

REM 检查 9900 端口是否已在运行(已在运行则直接打开浏览器)
netstat -ano | findstr ":9900" >nul 2>&1
if %errorlevel%==0 goto open_browser

echo [..] 正在启动网页版服务(后台运行, 本窗口可关闭)...
start "" "%PYTHON%" main.py --web --host 0.0.0.0 --port 9900

REM 等待服务就绪(最多等 20 秒)
set /a tries=0
:waitloop
ping -n 2 127.0.0.1 >nul
set /a tries+=1
netstat -ano | findstr ":9900" >nul 2>&1
if %errorlevel%==0 goto open_browser
if %tries% lss 20 goto waitloop
echo [!!] 服务启动较慢, 请稍后手动打开 http://127.0.0.1:9900/
ping -n 4 127.0.0.1 >nul
exit /b 1

:open_browser
echo [OK] 服务已就绪, 正在打开浏览器...
start "" http://127.0.0.1:9900/
echo 浏览器将自动打开 http://127.0.0.1:9900/ (如未自动打开请手动访问)
ping -n 4 127.0.0.1 >nul
exit /b 0
