@echo off
cd /d D:\7tan\7tanAI
.venv\Scripts\python.exe _recover_app.py > _recover_log.txt 2>&1
echo Exit: %ERRORLEVEL% >> _recover_log.txt
