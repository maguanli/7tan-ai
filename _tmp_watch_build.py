# -*- coding: utf-8 -*-
"""监控 rebuild.bat 构建进程，直到完成或失败"""
import subprocess, time, os, sys

log_path = r'D:\7tan\7tanAI\dist\build_log.txt'
out = r'D:\7tan\7tanAI\_tmp_build_watch.txt'

def get_pids():
    try:
        r = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*PyInstaller*' } | Select-Object -ExpandProperty ProcessId"],
            capture_output=True, text=True, timeout=20)
        return [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    except Exception as e:
        return []

def tail(path, n=15):
    try:
        with open(path, 'rb') as f:
            data = f.read()
        text = data.decode('utf-8', errors='replace')
        lines = text.splitlines()
        return lines[-n:]
    except Exception:
        return ['<log read error>']

result = []
start = time.time()
last_size = -1
stable_count = 0
done = False
final_status = 'TIMEOUT'

while time.time() - start < 1200:  # 最多等 20 分钟
    pids = get_pids()
    try:
        cur_size = os.path.getsize(log_path)
    except Exception:
        cur_size = -1

    # 检查完成标志
    try:
        with open(log_path, 'rb') as f:
            text = f.read().decode('utf-8', errors='replace')
    except Exception:
        text = ''

    if not pids:
        if cur_size == last_size:
            stable_count += 1
        else:
            stable_count = 0
        # 进程已退出且 10 秒无变化 → 构建结束
        if stable_count >= 2:
            if 'Build complete' in text:
                final_status = 'SUCCESS'
            elif 'ERROR' in text.upper() or 'Traceback' in text:
                final_status = 'FAILED'
            else:
                final_status = 'EXITED-NO-MARKER'
            done = True
            break

    last_size = cur_size
    time.sleep(5)

result.append('=== BUILD WATCH RESULT ===')
result.append('status: %s' % final_status)
result.append('duration: %.0f s' % (time.time() - start))
result.append('final log size: %d bytes' % cur_size)
result.append('')
result.append('--- FINAL TAIL 25 ---')
for l in tail(log_path, 25):
    result.append('| ' + l)
result.append('')
result.append('--- "Build complete" in log: %s' % ('Build complete' in text))
result.append('--- "ERROR" in log: %s' % ('ERROR' in text.upper()))
result.append('--- "Traceback" in log: %s' % ('Traceback' in text))

open(out, 'w', encoding='utf-8').write('\n'.join(result))
print('WATCH DONE:', final_status, '%.0fs' % (time.time() - start))
