import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ps = (
    "powershell -NoProfile -Command "
    "\"Get-CimInstance Win32_Process | "
    "Where-Object { $_.Name -like '*python*' -or $_.Name -like '*tts*' } | "
    "Select-Object ProcessId, Name, CommandLine | Format-List | Out-String -Width 400\""
)
r = subprocess.run(ps, capture_output=True, text=True, timeout=20)
print(r.stdout[:6000])
if r.stderr:
    print("ERR:", r.stderr[:1000])
