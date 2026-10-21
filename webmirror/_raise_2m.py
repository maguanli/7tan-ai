# -*- coding: utf-8 -*-
"""把 4ba5eb 的 max_pages 从 1000000 抬到 2000000。
顺序：快照 -> 优雅停任务 -> 停服务 -> 备份并改 _tasks.json -> 拉起服务 -> 验证。
不自动续抓（另起一步），每步打印，失败即停。"""
import subprocess, sys, os, time, socket, io, json, shutil, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = r'D:\7tan\7tanAI\webmirror'
PORT = 8000
API = 'http://127.0.0.1:%d' % PORT
IDX = os.path.join(BASE, 'downloads', '_tasks.json')
BAK = IDX + '.bak_before_2m'
TID = '20261011-063926-4ba5eb'
NEW_MAX = 2000000


def api_get(path, timeout=10):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def api_post(path, body=None, timeout=20):
    data = json.dumps(body or {}).encode('utf-8')
    req = urllib.request.Request(API + path, data=data,
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def port_open(port):
    s = socket.socket(); s.settimeout(0.5)
    try:
        s.connect(('127.0.0.1', port)); return True
    except Exception:
        return False
    finally:
        s.close()


def pids_on_port(port):
    out = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True,
                         text=True, errors='replace').stdout
    pids = set()
    for line in out.splitlines():
        p = line.split()
        if len(p) >= 5 and p[3] == 'LISTENING' and p[1].endswith(':' + str(port)):
            pids.add(p[4])
    return pids


def task_of(tid):
    return api_get('/api/tasks/%s' % tid).get('task', {})


print('=' * 64)
print('步骤 1：改前快照')
print('=' * 64)
print('  端口8000监听 :', port_open(PORT))
before = task_of(TID)
bs = before.get('stats', {})
print('  4ba5eb status    =', before.get('status'))
print('  4ba5eb max_pages =', before.get('config', {}).get('max_pages'))
print('  pages_total      =', bs.get('pages_total'))
print('  queue_size       =', bs.get('queue_size'))

print()
print('=' * 64)
print('步骤 2：优雅停止任务（让状态落盘，避免中断在写盘瞬间）')
print('=' * 64)
try:
    r = api_post('/api/tasks/%s/cancel' % TID)
    print('  cancel ->', r)
except Exception as e:
    print('  cancel 失败(可忽略):', e)
for i in range(30):
    time.sleep(1)
    st = task_of(TID).get('status')
    if st != 'running':
        print('  第 %ds 状态变为: %s' % (i + 1, st)); break
else:
    print('  ⚠ 30s 内仍是 running，继续往下走')
print('  停止时 pages_total =', task_of(TID).get('stats', {}).get('pages_total'))

print()
print('=' * 64)
print('步骤 3：停服务')
print('=' * 64)
pids = pids_on_port(PORT)
print('  占用8000的PID:', pids or '(无)')
for pid in pids:
    r = subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True,
                       text=True, errors='replace')
    print('  taskkill /PID %s /F -> rc=%d %s' % (pid, r.returncode,
                                                 (r.stdout or r.stderr).strip()[:80]))
for i in range(20):
    if not port_open(PORT):
        break
    time.sleep(0.5)
print('  端口已释放 :', not port_open(PORT))

print()
print('=' * 64)
print('步骤 4：备份并修改 _tasks.json（只改 4ba5eb 的 max_pages）')
print('=' * 64)
shutil.copy2(IDX, BAK)
print('  已备份 ->', os.path.basename(BAK))
data = json.load(open(IDX, encoding='utf-8'))
hit = 0
for t in data:
    if t.get('id') == TID:
        old = t['config'].get('max_pages')
        t['config']['max_pages'] = NEW_MAX
        hit += 1
        print('  %s : max_pages %s -> %s' % (TID, old, t['config']['max_pages']))
if hit != 1:
    print('  ✗ 命中 %d 条，异常，终止（不写回）' % hit); sys.exit(1)
json.dump(data, open(IDX, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
# 回读验证
chk = json.load(open(IDX, encoding='utf-8'))
for t in chk:
    if t.get('id') == TID:
        print('  回读验证 : max_pages =', t['config']['max_pages'])

print()
print('=' * 64)
print('步骤 5：拉起服务')
print('=' * 64)
DETACHED = 0x00000008
CREATE_NO_WINDOW = 0x08000000
log = open(os.path.join(BASE, '_server.log'), 'ab')
err = open(os.path.join(BASE, '_server.err'), 'ab')
proc = subprocess.Popen([sys.executable, 'run.py', '--port', str(PORT)], cwd=BASE,
                        stdout=log, stderr=err, stdin=subprocess.DEVNULL,
                        creationflags=DETACHED | CREATE_NO_WINDOW)
print('  新进程 PID =', proc.pid)
ready = False
for i in range(60):
    time.sleep(0.5)
    if port_open(PORT):
        try:
            api_get('/api/tasks', timeout=3)
            print('  第 %.1f 秒就绪 ✅' % ((i + 1) * 0.5)); ready = True; break
        except Exception:
            pass
if not ready:
    print('  ✗ 未就绪，看 _server.err 末尾')

print()
print('=' * 64)
print('步骤 6：重启后状态核验（预期 status=interrupted, max_pages=2000000）')
print('=' * 64)
after = task_of(TID)
print('  4ba5eb status    =', after.get('status'))
print('  4ba5eb max_pages =', after.get('config', {}).get('max_pages'))
print('  pages_total      =', after.get('stats', {}).get('pages_total'))
print('  queue_size       =', after.get('stats', {}).get('queue_size'))
print('  端口8000 :', port_open(PORT))
