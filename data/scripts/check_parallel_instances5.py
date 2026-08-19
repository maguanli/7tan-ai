# -*- coding: utf-8 -*-
"""追查 13248 实例的启动来源 + 两个实例详情"""
import subprocess, sys, json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ps = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in @(6216,2772,13248,11948)} | Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine | ConvertTo-Json -Compress"],
    capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=60)
out = ps.stdout.strip()
try:
    data = json.loads(out)
    if isinstance(data, dict):
        data = [data]
    for p in data:
        print(f"PID={p.get('ProcessId')}  父={p.get('ParentProcessId')}  {p.get('Name')}  启动={p.get('CreationDate')}")
        print(f"    CMD={(p.get('CommandLine') or '')[:250]}")
        print()
except Exception as e:
    print("解析失败:", e)
    print(out[:2000])

# 查两个实例各自打开的端口（如果主程序有 web 端口）
print("=" * 60)
print("端口监听情况（找主程序 web/ws 端口）")
print("=" * 60)
r = subprocess.run(['powershell', '-NoProfile', '-Command',
                    "Get-NetTCPConnection -State Listen | Where-Object {$_.OwningProcess -in @(13248,11948)} | Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress"],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=60)
print(r.stdout[:1500] if r.stdout.strip() else "两个实例均无监听端口（可能纯桌面模式）")
