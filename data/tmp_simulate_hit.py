# -*- coding: utf-8 -*-
import json, io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def tokenize(text):
    words = set()
    for m in re.findall(r'[\u4e00-\u9fa5]{2,6}|[A-Za-z0-9_]{2,}', text or ''):
        words.add(m)
        if len(m) >= 3:
            for i in range(len(m) - 1):
                words.add(m[i:i + 2])
    return words

query = '你会编程吗'
q_words = tokenize(query)
print('查询词:', sorted(q_words))

# ---- 1. knowledge 库（旧知识兜底）----
with open(r'D:\7tan\7tanAI\data\tan_model_memory.json', encoding='utf-8') as f:
    mem = json.load(f)
print('\n=== knowledge 命中模拟（2.6 旧知识库兜底）===')
for k in mem.get('knowledge', []):
    text = (k.get('key', '') or '') + ' ' + (k.get('content', '') or '')
    hit = sum(1 for w in q_words if w.lower() in text.lower())
    print(' key=%r 命中词数=%d -> %s' % (k.get('key'), hit, '会命中!' if hit > 0 else '不命中'))

# ---- 2. memory_library（2.5 长期记忆优先）----
with open(r'D:\7tan\7tanAI\data\tan_model_organs.json', encoding='utf-8') as f:
    org = json.load(f)
ml = org.get('memory_library', []) if isinstance(org, dict) else org
print('\n=== memory_library 命中模拟（2.5 长期记忆优先）===')
print('memory_library 总数:', len(ml))
hits = []
for idx, m in enumerate(ml):
    thought = str(m.get('thought', '') or '').strip()
    if not thought or thought.startswith('tool:'):
        continue
    hit = sum(1 for w in q_words if w.lower() in thought.lower())
    if hit > 0:
        hits.append((hit, idx, thought[:60]))
print('命中条数:', len(hits))
for hit, idx, t in sorted(hits, key=lambda x: (-x[0], -x[1]))[:15]:
    print('  [overlap=%d idx=%d] %s' % (hit, idx, t))
