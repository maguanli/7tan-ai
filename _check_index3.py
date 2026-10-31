# -*- coding: utf-8 -*-
import re, urllib.request, urllib.parse

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'ignore'), r.status

# 搜索表单长什么样
h, st = get('https://www.7tan.com/bbs/search.php')
print('search.php', st, len(h))
forms = re.findall(r'<form[^>]*>', h)
print('forms:', forms)
inputs = re.findall(r'<input[^>]*>', h)
for i in inputs[:10]:
    print('  input:', i[:160])
body = re.sub(r'<script.*?</script>', ' ', h, flags=re.S)
body = re.sub(r'<[^>]+>', ' ', body)
body = re.sub(r'\s+', ' ', body)
print('body:', body[:600])

# 试不同参数名
for param in ['keyword', 'kw', 'q', 'key', 'searchkey']:
    u = 'https://www.7tan.com/bbs/search.php?' + param + '=' + urllib.parse.quote('小小村长')
    try:
        hh, ss = get(u)
        ids = sorted(set(re.findall(r'/bbs/(\d{5})/', hh)))
        print('param', param, ss, len(hh), 'ids', len(ids), ids[:8])
    except Exception as e:
        print('param', param, 'ERR', e)
