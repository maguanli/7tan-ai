# -*- coding: utf-8 -*-
"""对比两个 7tanAI 实例的启动时间/窗口/父进程"""
import subprocess, sys, json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ps = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Select-Object ProcessId,ParentProcessId,CreationDate,ExecutablePath,CommandLine,MainWindowTitle | ConvertTo-Json -Compress"],
    capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=60)
out = ps.stdout.strip()
try:
    data = json.loads(out)
    if isinstance(data, dict):
        data = [data]
    for p in data:
        cmd = p.get('CommandLine') or ''
        if 'main.py' not in cmd:
            continue
        print(f"PID={p.get('ProcessId')}")
        print(f"  父进程PID={p.get('ParentProcessId')}")
        print(f"  启动时间={p.get('CreationDate')}")
        print(f"  可执行={p.get('ExecutablePath')}")
        print(f"  窗口标题={p.get('MainWindowTitle') or '(无)'}")
        print(f"  命令={cmd[:160]}")
        print()
except Exception as e:
    print("解析失败:", e)
    print(out[:2000])
