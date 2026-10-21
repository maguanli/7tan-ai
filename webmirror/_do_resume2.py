# -*- coding: utf-8 -*-
"""续抓 4ba5eb 并连续观测：验证从 ~64.4 万接着往下，不是重头。"""
import sys, io, time, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
API = 'http://127.0.0.1:8000'
TID = '20261011-063926-4ba5eb'


def get(path, timeout=10):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def post(path, body=None, timeout=30):
    data = json.dumps(body or {}).encode('utf-8')
    req = urllib.request.Request(API + path, data=data,
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


t0 = get('/api/tasks/%s' % TID)['task']
print('续抓前 : status=%s pages_total=%s queue=%s' %
      (t0['status'], t0['stats'].get('pages_total'), t0['stats'].get('queue_size')))
print('POST /resume ->', post('/api/tasks/%s/resume' % TID))
print()
print('%-8s | %-8s | %-10s | %-9s | %-9s' % ('t(s)', 'status', 'pages_total', 'pages_ok', 'queue'))
print('-' * 60)
start = time.time()
last = None
for i in range(0, 19):
    time.sleep(6 if i else 3)
    t = get('/api/tasks/%s' % TID)['task']
    s = t['stats']
    print('%-8.0f | %-8s | %-10s | %-9s | %-9s' %
          (time.time() - start, t['status'], s.get('pages_total'),
           s.get('pages_ok'), s.get('queue_size')))
    last = s
print()
print('=== 判定 ===')
if last:
    print('起始 pages_total = 644940 ; 结束 pages_total =', last.get('pages_total'))
    if last.get('pages_total', 0) >= 644940:
        print('>>> 未从 0 重来（只要 >= 644940 即证明续抓）✅')
# 看日志尾
try:
    lg = get('/api/tasks/%s/logs' % TID)
    logs = lg.get('logs', lg)
    print()
    print('=== 最近日志 ===')
    for ln in (logs[-12:] if isinstance(logs, list) else []):
        print('  ', ln.get('t'), ln.get('level'), ln.get('msg'))
except Exception as e:
    print('日志读取失败:', e)
