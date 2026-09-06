# -*- coding: utf-8 -*-
import json, io, sys, time, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = r'D:\7tan\7tanAI\data\tan_model_memory.json'
bak = r'D:\7tan\7tanAI\data\backups\tan_model_memory.before_clean_knowledge.%s.bak.json' % time.strftime('%Y%m%d_%H%M%S')
shutil.copy2(path, bak)
print('备份:', bak)

with open(path, 'r', encoding='utf-8') as f:
    d = json.load(f)

ks = d.get('knowledge', [])
print('修改前 knowledge 条数:', len(ks))
removed = []
kept = []
for k in ks:
    if k.get('key') == 'capability_boundary':
        removed.append(k)
    else:
        kept.append(k)
d['knowledge'] = kept
with open(path, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)

print('删除条数:', len(removed))
for k in removed:
    print('  removed key=%r content=%r' % (k.get('key'), (k.get('content') or '')[:80]))
print('剩余条数:', len(d['knowledge']))
for k in d['knowledge']:
    print('  kept key=%r' % k.get('key'))
print('DONE')
