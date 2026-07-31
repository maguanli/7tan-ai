# -*- coding: utf-8 -*-
"""启动 exe 并抓取窗口标题，确认弹窗内容"""
import subprocess, time

EXE = r"D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe"

proc = subprocess.Popen([EXE], cwd=r"D:\7tan\7tanAI\dist\7tan-editor")
time.sleep(10)

ps = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Get-Process 7tan-editor -ErrorAction SilentlyContinue | Select-Object Id, MainWindowTitle, Responding | Format-List; "
     "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object ProcessName, MainWindowTitle | Format-Table -AutoSize"],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
)
print(ps.stdout)

# 关闭
subprocess.run(["taskkill", "/F", "/IM", "7tan-editor.exe"], capture_output=True)
print("已清理进程")
