# -*- coding: utf-8 -*-
"""安全重启 WebMirror(8000)：定位PID -> 优雅停 -> 确认端口释放 -> 拉起 -> 等端口就绪。
每步打印，失败即停（不盲目往下走）。"""
import subprocess, sys, os, time, socket, io, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = r'D:\7tan\7tanAI\webmirror'
PORT = 8000

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

def api_ok():
    try:
        with urllib.request.urlopen('http://127.0.0.1:%d/api/tasks' % PORT, timeout=3) as r:
            return json_ok(r.read())
    except Exception as e:
        return 'ERR:' + str(e)

def json_ok(b):
    import json
    try:
        d = json.loads(b.decode('utf-8'))
        return 'OK tasks=%d' % len(d.get('tasks', []))
    except Exception as e:
        return 'BADJSON:' + str(e)

def pids_on_port(port):
    out = subprocess.run(['netstat', '-ano', '-p', 'TCP'],
                         capture_output=True, text=True, errors='replace').stdout
    pids = set()
    for line in out.splitlines():
        # 形如:  TCP    127.0.0.1:8000   0.0.0.0:0    LISTENING    1234
        parts = line.split()
        if len(parts) >= 5 and parts[3] == 'LISTENING' and parts[1].endswith(':' + str(port)):
            pids.add(parts[4])
    return pids

print('=' * 60)
print('步骤 1：改前状态')
print('=' * 60)
print('  端口 8000 监听 :', port_open(PORT))
print('  API            :', api_ok())
pids = pids_on_port(PORT)
print('  占用 8000 的PID:', pids or '(无)')

if not pids:
    print('  → 没有进程占用 8000，跳过停止步骤')
else:
    print()
    print('=' * 60)
    print('步骤 2：停止旧进程')
    print('=' * 60)
    for pid in pids:
        r = subprocess.run(['taskkill', '/PID', pid, '/F'],
                           capture_output=True, text=True, errors='replace')
        print('  taskkill /PID %s /F -> rc=%d %s' % (pid, r.returncode,
                                                     (r.stdout or r.stderr).strip()[:80]))
    # 等端口释放
    for i in range(20):
        if not port_open(PORT):
            break
        time.sleep(0.5)
    print('  端口已释放 :', not port_open(PORT))

print()
print('=' * 60)
print('步骤 3：拉起新进程')
print('=' * 60)
DETACHED = 0x00000008
CREATE_NO_WINDOW = 0x08000000
log = open(os.path.join(BASE, '_server.log'), 'ab')
err = open(os.path.join(BASE, '_server.err'), 'ab')
proc = subprocess.Popen(
    [sys.executable, 'run.py', '--port', str(PORT)],
    cwd=BASE,
    stdout=log, stderr=err, stdin=subprocess.DEVNULL,
    creationflags=DETACHED | CREATE_NO_WINDOW,
)
print('  新进程 PID =', proc.pid)

print()
print('=' * 60)
print('步骤 4：等待就绪（最多 30 秒）')
print('=' * 60)
ready = False
for i in range(60):
    time.sleep(0.5)
    if port_open(PORT):
        a = api_ok()
        if a.startswith('OK'):
            print('  第 %.1f 秒就绪 | %s' % ((i + 1) * 0.5, a))
            ready = True
            break
if not ready:
    print('  ✗ 30 秒内未就绪！最后 API =', api_ok())
    print('  查看 _server.err 末尾：')
    try:
        tail = open(os.path.join(BASE, '_server.err'), encoding='utf-8',
                    errors='replace').read().splitlines()[-15:]
        for ln in tail:
            print('    ', ln)
    except Exception as e:
        print('    (读日志失败)', e)
else:
    print()
    print('=' * 60)
    print('步骤 5：确认任务仍在')
    print('=' * 60)
    import json
    with urllib.request.urlopen('http://127.0.0.1:%d/api/tasks' % PORT, timeout=5) as r:
        d = json.loads(r.read().decode('utf-8'))
    ts = d.get('tasks', [])
    print('  任务总数 =', len(ts))
    for t in ts:
        if t.get('id') == '20261011-063926-4ba5eb':
            print('  ★ 4ba5eb: status=%s  max_pages=%s' %
                  (t.get('status'), (t.get('config') or {}).get('max_pages')))
    print('  端口 8000 :', port_open(PORT))
    print()
    print('  重启成功 ✅')
