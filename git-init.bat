@echo off
cd /d D:\7tan\7tanAI

echo === 初始化 Git 仓库 ===
git init
git add .gitignore requirements.txt main.py src/ data/prompts/ *.spec rebuild.bat start.bat start.sh ARCHITECTURE.md test_debug.bat build.bat .env.example
git commit -m "初始提交: 7tanAI 游戏资源采编工具"

echo.
echo === 仓库状态 ===
git log --oneline -3
git status
pause
