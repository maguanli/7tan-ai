@echo off
cd /d D:\7tan\7tanAI
call .venv\Scripts\activate.bat
python -c "from PyQt6.QtWebEngineWidgets import QWebEngineView; print('PyQt6 OK')"
echo Exit code: %errorlevel%
pause
