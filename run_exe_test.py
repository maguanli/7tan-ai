# -*- coding: utf-8 -*-
"""直接运行 exe，检查进程存活 + 抓 Windows 错误事件"""
import subprocess, time, os

EXE = r"D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe"

# 启动 exe
proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE))
print("已启动 exe，PID:", proc.pid)

# 等待 15 秒（给 QtWebEngine 初始化时间）
time.sleep(15)

if proc.poll() is None:
    print("\n>>> 进程仍然存活（15 秒后）==> 启动成功")
    proc.terminate()
else:
    print("\n>>> 进程已退出！退出码:", proc.returncode, "==> 启动失败")

# 抓 Windows Application 事件日志中的错误
print("\n=== 最近 Application Error / .NET Runtime 事件 ===")
ps = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Get-WinEvent -LogName Application -MaxEvents 30 | Where-Object {$_.ProviderName -match 'Application Error|Windows Error|.NET Runtime'} | Select-Object -First 5 TimeCreated, ProviderName, @{n='Msg';e={$_.Message.Substring(0, [Math]::Min(600, $_.Message.Length))}} | Format-List"],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
)
print(ps.stdout)
print(ps.stderr[:2000] if ps.stderr else "")
