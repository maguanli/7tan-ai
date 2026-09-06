# -*- coding: utf-8 -*-
import subprocess, datetime, os

def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20)
        return (r.stdout or '').strip()
    except Exception as e:
        return f'ERR:{e}'

# 1. 进程 6168 启动时间
print('== PID 6168 ==')
print(run(['wmic', 'process', 'where', 'processid=6168', 'get', 'CreationDate', '/value']))
print(run(['powershell', '-NoProfile', '-Command', "(Get-Process -Id 6168 -ErrorAction SilentlyContinue).StartTime.ToString('yyyy-MM-dd HH:mm:ss')"]))

# 2. 文件修改时间
for f in ['src/agent/world_model.py', 'src/agent/bionic_organs.py', 'src/agent/self_learn.py']:
    try:
        t = datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M:%S')
        print(f'{f}: {t}')
    except Exception as e:
        print(f'{f}: ERR {e}')

# 3. 现在时间
print('now:', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
