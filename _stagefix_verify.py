# -*- coding: utf-8 -*-
"""改后核验：语法编译 / 行尾 / 关键片段 / 真实落盘数据复算。"""
import io
import sys
import json
import hashlib
import py_compile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(r'D:\7tan\7tanAI')

print('=== 1) 语法编译 ===')
for rel in ['src/agent/upper_m2_autobiography.py', 'src/web/routes/api_mind.py']:
    p = ROOT / rel
    try:
        py_compile.compile(str(p), doraise=True)
        print('  [OK]  ', rel)
    except Exception as e:
        print('  [FAIL]', rel, e)

print('=== 2) 行尾 & MD5 ===')
for rel in ['src/agent/upper_m2_autobiography.py', 'src/web/routes/api_mind.py']:
    p = ROOT / rel
    b = p.read_bytes()
    print('  %-34s %7d B  md5=%s  CRLF=%d  LF=%d' % (
        p.name, len(b), hashlib.md5(b).hexdigest(), b.count(b'\r\n'), b.count(b'\n')))

print('=== 3) 关键片段确认（旧写法应为 0）===')
checks = [
    ('src/agent/upper_m2_autobiography.py',
     ['M2_KEY_MEMORY_MAX = 200', 'key[-M2_KEY_MEMORY_MAX:]', 'key[:20]']),
    ('src/web/routes/api_mind.py',
     ['_M2_STAGE_DISPLAY_MAX = 60', 'all_stages[-_M2_STAGE_DISPLAY_MAX:]', 'len(all_stages)',
      'stages") or [])[:20]']),
]
for rel, keys in checks:
    t = (ROOT / rel).read_text(encoding='utf-8')
    print(' ', rel)
    for k in keys:
        print('    %-38s x%d' % (k, t.count(k)))

print('=== 4) 真实落盘数据复算 ===')
P = ROOT / 'data/tan_model_organs.json'
d = json.loads(P.read_text(encoding='utf-8'))
mem = d.get('memory_library') or []
mems = [(m, i) for i, m in enumerate(mem) if isinstance(m, dict) and m.get('thought')]
mems.sort(key=lambda x: float(x[0].get('subjective_time', 0.0) or 0.0))
GAP = 30.0
stages = []
cur = None
for m, idx in mems:
    subj = float(m.get('subjective_time', 0.0) or 0.0)
    if cur is None or subj - cur['end_subj'] > GAP:
        if cur is not None:
            stages.append(cur)
        cur = {'start_subj': subj, 'end_subj': subj, 'count': 0}
    cur['end_subj'] = subj
    cur['count'] += 1
if cur is not None:
    stages.append(cur)
key = [(m, i) for m, i in mems
       if float(m.get('focus', 0.0)) >= 0.3 or abs(float(m.get('valence', 0.0))) >= 0.2]
print('  记忆库(落盘)         =', len(mem))
print('  真实阶段数(全量)     =', len(stages), '  <- 改后 stage_count 显示这个')
print('  关键经历(全量)       =', len(key))
print('  关键经历(取最近200)  =', len(key[-200:]))
print('  展示最近阶段数       =', min(len(stages), 60))
