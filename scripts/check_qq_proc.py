# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import subprocess

# 用 wmic 查进程（tasklist 之前卡住）
try:
    out = subprocess.run(
        'wmic process where "name like \'%QQ%\'" get ProcessId,Name,ExecutablePath /format:list',
        capture_output=True, text=True, encoding='gbk', errors='replace', timeout=20
    ).stdout
    print('=== wmic QQ 进程 ===')
    print(out if out.strip() else '(无)')
except Exception as e:
    print('wmic err:', e)

# 备用：powershell Get-Process
try:
    out = subprocess.run(
        'powershell -NoProfile -Command "Get-Process | Where-Object {$_.Name -like \'*QQ*\'} | Select-Object Id,Name,Path | Format-List"',
        capture_output=True, text=True, encoding='gbk', errors='replace', timeout=30
    ).stdout
    print('=== PS QQ 进程 ===')
    print(out if out.strip() else '(无)')
except Exception as e:
    print('ps err:', e)
