# -*- coding: utf-8 -*-
"""只读侦查：核对 4ba5eb 任务的配置与续抓状态，不修改任何文件。"""
import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = r'D:\7tan\7tanAI\webmirror'
DL = os.path.join(ROOT, 'downloads')
TASKS = os.path.join(DL, '_tasks.json')
TID = '20261011-063926-4ba5eb'

print('=' * 60)
print('1) _tasks.json 结构')
print('=' * 60)
raw = json.load(open(TASKS, encoding='utf-8'))
print('top-level type:', type(raw).__name__)
if isinstance(raw, dict):
    for k in raw.keys():
        print('  key:', k)

def find_task(obj, tid):
    """在任意嵌套结构里找 id==tid 的记录，返回 (path, dict)"""
    hits = []
    def walk(o, path):
        if isinstance(o, dict):
            if o.get('id') == tid or o.get('task_id') == tid:
                hits.append((path, o))
            for k, v in o.items():
                walk(v, path + '/' + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + '[%d]' % i)
    walk(obj, '')
    return hits

hits = find_task(raw, TID)
print()
print('=' * 60)
print('2) 该任务在 _tasks.json 里的记录（找到 %d 处）' % len(hits))
print('=' * 60)
for path, rec in hits:
    print('path:', path)
    rec2 = dict(rec)
    # 精简：只打印关键字段
    for k in ('id', 'task_id', 'url', 'start_url', 'status', 'created_at', 'updated_at'):
        if k in rec2:
            print('  %s = %r' % (k, rec2[k]))
    cfg = rec2.get('config') or rec2.get('params') or {}
    if isinstance(cfg, dict):
        print('  --- config ---')
        for k in sorted(cfg.keys()):
            print('    %s = %r' % (k, cfg[k]))
    prog = rec2.get('progress') or {}
    if isinstance(prog, dict):
        print('  --- progress ---')
        for k in sorted(prog.keys()):
            print('    %s = %r' % (k, prog[k]))
    print()

print('=' * 60)
print('3) 任务目录状态文件')
print('=' * 60)
tdir = os.path.join(DL, TID)
for fn in sorted(os.listdir(tdir)):
    fp = os.path.join(tdir, fn)
    if os.path.isfile(fp):
        print('  %-28s %10.1f MB' % (fn, os.path.getsize(fp) / 1048576))
    else:
        print('  %-28s <dir>' % fn)

print()
print('=' * 60)
print('4) _mirror_state.json 顶层结构（只读 key，不打印大内容）')
print('=' * 60)
sp = os.path.join(tdir, '_mirror_state.json')
if os.path.exists(sp):
    st = json.load(open(sp, encoding='utf-8'))
    if isinstance(st, dict):
        for k, v in st.items():
            if isinstance(v, (dict, list)):
                print('  %s : %s(len=%d)' % (k, type(v).__name__, len(v)))
            else:
                print('  %s = %r' % (k, v))
    else:
        print('  type:', type(st).__name__, 'len=', len(st) if hasattr(st, '__len__') else '?')
else:
    print('  NOT FOUND')

print()
print('=' * 60)
print('5) _mirror_report.txt 末尾 30 行')
print('=' * 60)
rp = os.path.join(tdir, '_mirror_report.txt')
if os.path.exists(rp):
    lines = open(rp, encoding='utf-8', errors='replace').read().splitlines()
    for ln in lines[-30:]:
        print(' ', ln)
else:
    print('  NOT FOUND')
