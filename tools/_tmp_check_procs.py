# -*- coding: utf-8 -*-
"""查询所有 python.exe 进程的 PID/父PID/命令行（用于确认是否双实例）"""
import subprocess

r = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | ForEach-Object { $_.ProcessId.ToString() + '|' + $_.ParentProcessId.ToString() + '|' + $_.CommandLine }"],
    capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)

print('STDOUT:')
print(r.stdout)
print('STDERR:')
print(r.stderr[:500] if r.stderr else '(none)')
