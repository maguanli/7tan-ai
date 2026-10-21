# -*- coding: utf-8 -*-
"""把 4ba5eb 任务的 max_pages 改到 1000000。先备份，改后回读验证。"""
import json, os, sys, io, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

IDX = r'D:\7tan\7tanAI\webmirror\downloads\_tasks.json'
BAK = IDX + '.bak_before_resume'
TID = '20261011-063926-4ba5eb'
NEW_MAX = 1000000

# 1) 备份
if not os.path.exists(BAK):
    shutil.copy2(IDX, BAK)
    print('[备份] 已创建', BAK)
else:
    print('[备份] 已存在（未覆盖）', BAK)

# 2) 读取
data = json.load(open(IDX, encoding='utf-8'))
assert isinstance(data, list), 'index 不是 list'
print('[读取] 任务数 =', len(data))

hit = None
for t in data:
    if t.get('id') == TID:
        hit = t
        break
assert hit is not None, '找不到任务 ' + TID

cfg = hit.setdefault('config', {})
old = cfg.get('max_pages')
print('[改前] id=%s  max_pages=%r  out_root=%r' % (TID, old, cfg.get('out_root')))

# 3) 改
cfg['max_pages'] = NEW_MAX

# 4) 写回（原子：先写临时再替换）
tmp = IDX + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
os.replace(tmp, IDX)
print('[写入] 完成')

# 5) 回读验证
data2 = json.load(open(IDX, encoding='utf-8'))
for t in data2:
    if t.get('id') == TID:
        c = t.get('config', {})
        print('[回读] id=%s  max_pages=%r' % (t.get('id'), c.get('max_pages')))
        print('[回读] resume=%r  out_root=%r' % (c.get('resume'), c.get('out_root')))
        print('[回读] start_url=%r' % c.get('start_url'))
        break

# 6) 顺带把所有任务的关键字段打印一遍（确认没误伤别的）
print()
print('[全表] 各任务 max_pages：')
for t in data2:
    c = t.get('config', {})
    print('   %-24s  max_pages=%-8s  status=%s' % (t.get('id'), c.get('max_pages'), t.get('status')))
