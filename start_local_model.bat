@echo off
chcp 65001 >nul
title 7Tan 本地模型启动器
echo ============================================
echo   7Tan 本地 AI 内核（1.1GB 方案）
echo   Qwen2.5-1.5B-Instruct-q4_K_M (986MB, 离线)
echo ============================================
echo.
netstat -ano | findstr :18080 >nul 2>&1
if %errorlevel%==0 (
    echo [OK] 本地模型已在运行 (127.0.0.1:18080)，无需重复启动。
    echo      直接启动 7Tan 即可使用。
    goto :end
)
echo [启动] 正在拉起 llama-server ... 首次加载约 5~30 秒
start "7Tan-LocalModel" /min D:\7tan\7tanAI\models\llama.cpp\llama-server.exe -m D:\7tan\7tanAI\models\gguf\Qwen2.5-1.5B-Instruct-q4_K_M.gguf -c 4096 --host 127.0.0.1 --port 18080 --threads 4 -ngl 0
echo [等待] 模型加载中，请稍候...
set /a n=0
:wait
timeout /t 2 /nobreak >nul
set /a n+=1
netstat -ano | findstr :18080 >nul 2>&1
if %errorlevel%==0 (
    echo [OK] 本地模型就绪！(等待 %n% 次探测)
    goto :end
)
if %n% lss 20 goto :wait
echo [警告] 30 秒内未检测到服务，请查看 data\llama_server.log
:end
echo.
echo 提示：停止服务请运行 stop_local_model.bat
pause
