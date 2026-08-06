import sys
import ctypes
import ctypes.wintypes as wt

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

u = ctypes.windll.user32

# 恢复 PowerShell 看一眼（不激活，只读窗口文字需要它在前台……先跳过，直接查进程）
# 查 10912 的父进程和启动时间
import subprocess

ps = (
    'powershell -NoProfile -Command "'
    '$p = Get-CimInstance Win32_Process -Filter \\"ProcessId=10912\\"; '
    '$pp = Get-CimInstance Win32_Process -Filter \\"ProcessId=$($p.ParentProcessId)\\"; '
    'Write-Output (\\"PID: \\" + $p.ProcessId); '
    'Write-Output (\\"Parent: \\" + $p.ParentProcessId + \\" name: \\" + $pp.Name); '
    'Write-Output (\\"Created: \\" + $p.CreationDate); '
    'Write-Output (\\"Cmd: \\" + $p.CommandLine)\"'
)
r = subprocess.run(ps, capture_output=True, text=True, timeout=20)
print(r.stdout[:1500], flush=True)
if r.stderr:
    print("ERR:", r.stderr[:500], flush=True)
