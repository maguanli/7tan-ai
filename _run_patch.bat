@echo off
chcp 65001 >nul
echo Running rename patch...
"C:\Program Files\Python312\python.exe" "D:\7tan\7tanAI\_rename_patch.py"
del "D:\7tan\7tanAI\_rename_patch.py"
del "%~f0"
echo Done.
