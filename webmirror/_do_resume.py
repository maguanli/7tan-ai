# -*- coding: utf-8 -*-
"""触发续抓，并持续观察 60 秒，确认它真的在"接着抓"而不是从零/空转。"""
import json, sys, io, time, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
API = 'http://127.0.0.1:8000'
TID = '20261011-063926-4ba5eb'

def get(path):
    with urllib.request.urlopen(API + path, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

def post(path):
    req = urllib.request.Request(API + path, method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))

print('=' * 60)
print('触发续抓：POST /api/tasks/%s/resume' % TID)
print('=' * 60)
try:
    r = post('/api/tasks/%s/resume' % TID)
    print('  响应:', r)
except Exception as e:
    print('  请求失败:', e)
    sys.exit(1)

print()
print('=' * 60)
print('观察 60 秒（每 6 秒采一次）')
print('=' * 60)
hdr = '  %6s | %-9s | %10s | %10s | %8s | %7s' % (
    '时刻', 'status', 'pages_total', 'pages_ok', 'queue', '文件数')
print(hdr)
print('  ' + '-' * 66)

last = None
for i in range(11):
    time.sleep(6)
    try:
        d = get('/api/tasks/%s' % TID)
        t = d.get('task', d)
        st = t.get('stats') or {}
        line = '  %5ds | %-9s | %10s | %10s | %8s | %7s' % (
            (i + 1) * 6,
            t.get('status'),
            st.get('pages_total'),
            st.get('pages_ok'),
            st.get('queue_size'),
            st.get('files'),
        )
        print(line)
        last = st
    except Exception as e:
        print('  %5ds | 读取失败: %s' % ((i + 1) * 6, e))

print()
print('=' * 60)
print('最近日志（尾部 20 条）')
print('=' * 60)
try:
    d = get('/api/tasks/%s/logs?since=0' % TID)
    for lg in (d.get('logs') or [])[-20:]:
        print('  [%s] %s %s' % (lg.get('t', ''), lg.get('level', ''), lg.get('msg', '')))
except Exception as e:
    print('  读日志失败:', e)
