@echo off
chcp 936 >nul 2>&1
setlocal
cd /d "%~dp0"
title 7Tan 网页版服务启动器

set "EXE=%~dp07tan-editor\7tan-editor.exe"
set "PYW=%~dp0.venv\Scripts\pythonw.exe"
set "URL=http://127.0.0.1:9900/"

echo ==========================================
echo   7Tan 网页版服务（一键启动，适用于 Windows 10/11 64位）
echo   - 绿色版免安装，无需安装 Python / Node.js
echo   - 首次运行自动配置开机自启
echo ==========================================
echo.

if exist "%EXE%" (
    rem ====== 绿色版模式：exe 自带运行环境 ======
    echo [1/3] 配置开机自启...
    "%EXE%" --web-autostart install
    echo [2/3] 启动网页版服务...
    "%EXE%" --web-autostart launch
) else if exist "%PYW%" (
    rem ====== 开发模式：使用项目虚拟环境 ======
    echo [1/3] 配置开机自启...
    "%PYW%" "%~dp0tools\web_autostart.py" --install
    echo [2/3] 启动网页版服务...
    "%PYW%" "%~dp0tools\web_autostart.py" --launch
) else (
    echo.
    echo [错误] 未找到 7tan-editor.exe 或开发运行环境！
    echo        请检查软件目录是否完整（解压完整 ZIP 包）。
    echo.
    pause
    exit /b 1
)

echo [3/3] 打开浏览器...
start "" "%URL%"
echo.
echo 完成！网页版地址: %URL%
echo 以后开机自动运行，随时直接访问即可。
timeout /t 3 /nobreak >nul
exit /b 0
