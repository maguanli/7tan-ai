@echo off
cd /d "D:\7tan\7tanAI"
echo Copying qq_bridge plugin fix...
copy /Y "data\plugins\qq_bridge\tools.py" "dist\7tan-editor\_internal\data\plugins\qq_bridge\tools.py"
echo Done!
pause
