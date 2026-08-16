@echo off
rem DeepSeek Harness (dsh) 启动脚本 - 带防重复启动保护
rem 若 3080 端口已被监听（dsh 已在运行），直接退出，避免重复实例
netstat -ano | findstr ":3080" | findstr "LISTENING" >nul 2>nul
if %errorlevel%==0 (
    exit /b 0
)
cd /d G:\nodejs\node-v24.19.0-win-x64
start "dsh-web" /min cmd /c "node.exe node_modules\@deepseek-ai\dsh\lib\bin.js web > D:\7tan\7tanAI\logs\dsh_web.log 2> D:\7tan\7tanAI\logs\dsh_web_err.log"
