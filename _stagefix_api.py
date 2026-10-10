# -*- coding: utf-8 -*-
"""抓取 /api/mind/status 的 growth 字段（改前/改后对照用）。"""
import io
import sys
import json
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

url = 'http://127.0.0.1:9900/api/mind/status'
d = json.loads(urllib.request.urlopen(url, timeout=20).read().decode('utf-8'))
g = d.get('growth') or {}
print('subj_now         =', g.get('subj_now'))
print('memory_count     =', g.get('memory_count'))
print('key_memory_count =', g.get('key_memory_count'))
print('traceable_count  =', g.get('traceable_count'))
print('stage_count      =', g.get('stage_count'))
st = g.get('stages') or []
print('stages list len  =', len(st))
if st:
    print('  first:', st[0])
    print('  last :', st[-1])
