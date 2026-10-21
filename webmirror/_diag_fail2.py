# -*- coding: utf-8 -*-
import json, os, io, sys, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'
st = json.load(open(os.path.join(d, '_mirror_state.json'), encoding='utf-8'))
errors = st.get('errors') or []
s = st['stats']

print('=== 计数口径 ===')
print('pages_ok    %d' % s['pages_ok'])
print('pages_fail  %d   (抓取异常)' % s['pages_fail'])
print('skipped     %d   (worker 层异常，另计)' % s['skipped'])
print('errors 列表 %d   (= pages_fail + skipped = %d)' % (len(errors), s['pages_fail'] + s['skipped']))
print('pages_total %d  (= ok+fail+skipped? %d)' % (s['pages_total'], s['pages_ok'] + s['pages_fail'] + s['skipped']))

print()
print('=== 失败原因分类 ===')
cat = collections.Counter()
for e in errors:
    msg = e.get('error', '')
    if 'getaddrinfo' in msg:
        cat['DNS 解析失败 (Errno 11001)'] += 1
    elif 'WinError 32' in msg:
        cat['文件被占用 (WinError 32)'] += 1
    elif 'WinError 2' in msg:
        cat['文件找不到 (WinError 2)'] += 1
    else:
        cat['其他: ' + msg[:40]] += 1
for k, v in cat.most_common():
    print('  %-34s %d' % (k, v))

print()
print('=== 失败 URL 是否还在流水账里（决定下次续抓会不会重试）===')
jp = os.path.join(d, '_mirror_queue.ndjson')
if os.path.exists(jp):
    jset = set()
    n = 0
    with open(jp, encoding='utf-8', errors='replace') as f:
        for line in f:
            n += 1
            line = line.strip()
            if not line:
                continue
            try:
                it = json.loads(line)
                u = it.get('url')
                if u:
                    jset.add(u)
            except Exception:
                pass
    print('流水账行数 %d   唯一 URL %d' % (n, len(jset)))
    in_j = sum(1 for e in errors if e['url'] in jset)
    print('失败 URL 在流水账里的: %d / %d' % (in_j, len(errors)))
    print('流水账(曾入队) 总数 = %d' % len(jset))

print()
print('=== 上限还有多远 ===')
cap = 1000000
pt = s['pages_total']
q = s['queue_size']
print('已计入 pages_total : %d' % pt)
print('当前待抓 queue_size: %d' % q)
print('距 1,000,000 上限   : %d 页可抓' % (cap - pt))
print('若把队列清空        : 会到 %d 页' % (pt + q))
print('=> 会不会撞上限     : %s' % ('会（超出 %d 页仍抓不完）' % (pt + q - cap) if pt + q > cap else '不会'))
