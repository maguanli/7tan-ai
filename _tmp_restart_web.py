# -*- coding: utf-8 -*-
"""重启 9900 Web 服务：杀旧进程(旧代码) -> 启动新进程(加载 2ed0b94 修复)"""
import subprocess, time, os, sys

PYW = r"C:\Program Files\Python312\pythonw.exe"
ROOT = r"D:\7tan\7tanAI"
CREATE_NO_WINDOW = 0x08000000

# 1) 按命令行精确找到 9900 服务的进程并杀掉（避免误杀其他 pythonw）
killed = []
try:
    r = subprocess.run(['wmic', 'process', 'where', "name='pythonw.exe'", 'get', 'ProcessId,CommandLine', '/format:csv'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20)
    for line in (r.stdout or '').splitlines():
        if 'main.py' in line and '9900' in line and ',' in line:
            pid = line.split(',')[1].strip()
            if pid.isdigit():
                subprocess.run(['taskkill', '/f', '/pid', pid], capture_output=True, timeout=15)
                killed.append(pid)
                print(f'killed pid={pid}')
except Exception as e:
    print(f'kill scan err: {e}')

# 兜底：若上面没杀掉，直接按 6168 杀
if not killed:
    try:
        subprocess.run(['taskkill', '/f', '/pid', '6168'], capture_output=True, timeout=15)
        print('killed pid=6168 (fallback)')
    except Exception as e:
        print(f'fallback kill err: {e}')

time.sleep(2)

# 2) 重新启动服务（隐藏窗口，后台运行）
try:
    p = subprocess.Popen(
        [PYW, os.path.join(ROOT, 'main.py'), '--web', '--host', '0.0.0.0', '--port', '9900'],
        cwd=ROOT, creationflags=CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f'started new pid={p.pid}')
except Exception as e:
    print(f'start err: {e}')

# 3) 等待服务就绪（最多 30 秒）
ok = False
for i in range(30):
    time.sleep(1)
    try:
        import urllib.request
        with urllib.request.urlopen('http://127.0.0.1:9900/api/health', timeout=3) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            if resp.status == 200 and 'ok' in body:
                ok = True
                print(f'health OK after {i+1}s: {body}')
                break
    except Exception:
        pass
print('READY' if ok else 'NOT_READY')
