# -*- coding: utf-8 -*-
import json, os, io, sys, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'

print('=== 目录文件 ===')
for f in sorted(os.listdir(d)):
    p = os.path.join(d, f)
    if os.path.isfile(p):
        print('  %-28s %10.1f KB' % (f, os.path.getsize(p)/1024))
    else:
        print('  [dir] %s' % f)

st = os.path.join(d, '_mirror_state.json')
if os.path.exists(st):
    j = json.load(open(st, encoding='utf-8'))
    print()
    print('=== _mirror_state.json ===')
    print('version      :', j.get('version'))
    print('updated_at   :', j.get('updated_at'))
    print('done         :', j.get('done'))
    s = j.get('stats') or {}
    print('pages_ok     :', s.get('pages_ok'))
    print('pages_fail   :', s.get('pages_fail'))
    print('assets_ok    :', s.get('assets_ok'), ' assets_fail:', s.get('assets_fail'))
    print('skipped      :', s.get('skipped'))
    print('pages_total  :', s.get('pages_total'))
    print('visited_cnt  :', j.get('visited_count'), ' pending_cnt:', j.get('pending_count'))
    e = j.get('errors') or []
    print('errors(快照里保留条数):', len(e))
    for x in e[:30]:
        print('   -', x.get('url'), '=>', x.get('error'))
    print('   ...(只列前30，最多保留1000)')

# _mirror_report.txt 是否存在
rp = os.path.join(d, '_mirror_report.txt')
print()
print('=== _mirror_report.txt 存在? ===', os.path.exists(rp))
if os.path.exists(rp):
    txt = open(rp, encoding='utf-8').read()
    lines = txt.splitlines()
    print('行数:', len(lines))
    for l in lines[:20]:
        print('   ', l)
    # 找失败列表段
    if '失败列表' in txt:
        idx = txt.index('失败列表')
        print('   [失败列表片段]')
        for l in txt[idx:].splitlines()[:20]:
            print('     ', l)
