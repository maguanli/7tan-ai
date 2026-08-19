@echo off
cd /d D:\7tan\7tanAI
echo === 快速 Git 备份 ===
git add -A
git commit -m "quick-save: %date% %time%"
echo.
git log --oneline -3
