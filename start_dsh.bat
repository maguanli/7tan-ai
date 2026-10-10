@echo off
rem DeepSeek Harness (dsh) 启动脚本 - 带防重复启动保护
rem 若 3080 端口已被监听（dsh 已在运行），直接退出，避免重复实例
netstat -ano | findstr ":3080" | findstr "LISTENING" >nul 2>nul
if %errorlevel%==0 (
    exit /b 0
)

rem 【修复 MISSING_CREDENTIAL】从 7Tan 的 .env 读取 DEEPSEEK_API_KEY 注入本进程环境，
rem 否则 dsh 独立进程读不到 Key，调用 DeepSeek 会报 no API key for provider route
for /f "usebackq tokens=1,* delims==" %%a in ("D:\7tan\7tanAI\.env") do (
    if /i "%%a"=="DEEPSEEK_API_KEY" set "DEEPSEEK_API_KEY=%%b"
)

cd /d D:\nodejs\node-v22.16.0-win-x64
start "dsh-web" /min cmd /c "D:\nodejs\node-v24.19.0-win-x64\node.exe node_modules\@deepseek-ai\dsh\lib\bin.js web > D:\7tan\7tanAI\logs\dsh_web.log 2> D:\7tan\7tanAI\logs\dsh_web_err.log"
