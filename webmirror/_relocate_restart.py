# -*- coding: utf-8 -*-
"""把 youbian.293.net 的后续落盘位置改到 youbian.293.net2，并重启 WebMirror。

顺序很关键：必须先停服务、再改 _tasks.json、最后拉起，
否则运行中的服务会把 _tasks.json 覆盖回去。
"""
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = r'D:\7tan\7tanAI\webmirror'
PORT = 8000
TID = '20261011-063926-4ba5eb'
IDX = os.path.join(BASE, 'downloads', '_tasks.json')
NEWMAP = {'youbian.293.net': 'youbian.293.net2'}


def port_open(port):
    s = socket.socket()
    s.settimeout(0.5)
    try:
        s.connect(('127.0.0.1', port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def pids_on_port(port):
    out = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True,
                         text=True, errors='replace').stdout
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3] == 'LISTENING' and parts[1].endswith(':' + str(port)):
            pids.add(parts[4])
    return pids


print('=' * 66)
print('步骤 1：停止 WebMirror（8000）')
print('=' * 66)
pids = pids_on_port(PORT)
print('  占用 8000 的 PID:', pids or '(无)')
for pid in pids:
    r = subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True,
                       text=True, errors='replace')
    print('  taskkill %s -> rc=%d' % (pid, r.returncode))
for _ in range(20):
    if not port_open(PORT):
        break
    time.sleep(0.5)
print('  端口已释放:', not port_open(PORT))

print()
print('=' * 66)
print('步骤 2：改 _tasks.json（先备份）')
print('=' * 66)
bak = IDX + '.bak_' + time.strftime('%Y%m%d_%H%M%S')
shutil.copy2(IDX, bak)
print('  备份 ->', os.path.basename(bak))

with open(IDX, 'r', encoding='utf-8') as f:
    data = json.load(f)

hit = None
for t in data:
    if t.get('id') == TID:
        hit = t
        break
if hit is None:
    print('  ✗ 找不到任务', TID)
    sys.exit(1)

cfg = hit.setdefault('config', {})
print('  改前 host_dir_map =', cfg.get('host_dir_map', '(无)'))
cfg['host_dir_map'] = NEWMAP
print('  改后 host_dir_map =', cfg['host_dir_map'])

with open(IDX, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('  已写入')

with open(IDX, 'r', encoding='utf-8') as f:
    back = json.load(f)
ok = any(t.get('id') == TID and t.get('config', {}).get('host_dir_map') == NEWMAP for t in back)
print('  回读校验:', 'OK' if ok else '✗ 失败')
if not ok:
    sys.exit(1)

print()
print('=' * 66)
print('步骤 3：拉起 WebMirror（加载新代码 + 新配置）')
print('=' * 66)
DETACHED = 0x00000008
NO_WINDOW = 0x08000000
log = open(os.path.join(BASE, '_server.log'), 'ab')
err = open(os.path.join(BASE, '_server.err'), 'ab')
proc = subprocess.Popen([sys.executable, 'run.py', '--port', str(PORT)], cwd=BASE,
                        stdout=log, stderr=err, stdin=subprocess.DEVNULL,
                        creationflags=DETACHED | NO_WINDOW)
print('  新进程 PID =', proc.pid)

print()
print('=' * 66)
print('步骤 4：等待就绪')
print('=' * 66)
ready = False
for i in range(60):
    time.sleep(0.5)
    if port_open(PORT):
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d/api/health' % PORT, timeout=3) as r:
                d = json.loads(r.read().decode('utf-8'))
            print('  第 %.1f 秒就绪 | tasks=%s' % ((i + 1) * 0.5, d.get('tasks')))
            ready = True
            break
        except Exception:
            pass
if not ready:
    print('  ✗ 未就绪，看 _server.err 末尾')
    try:
        tail = open(os.path.join(BASE, '_server.err'), encoding='utf-8',
                    errors='replace').read().splitlines()[-15:]
        for ln in tail:
            print('    ', ln)
    except Exception as e:
        print('   ', e)
    sys.exit(1)

print()
print('=' * 66)
print('步骤 5：确认任务配置已生效')
print('=' * 66)
with urllib.request.urlopen('http://127.0.0.1:%d/api/tasks/%s' % (PORT, TID), timeout=10) as r:
    t = json.loads(r.read().decode('utf-8'))['task']
print('  status       =', t.get('status'))
print('  host_dir_map =', t.get('config', {}).get('host_dir_map', '(无)'))
print('  concurrency  =', t.get('config', {}).get('concurrency'))
print('  delay        =', t.get('config', {}).get('delay'))
print('  用 ID 启动时间戳 =', t.get('started_at'))
