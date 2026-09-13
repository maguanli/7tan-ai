# -*- coding: utf-8 -*-
import json
from collections import defaultdict

d = json.load(open(r'D:\7tan\7tanAI\data\screenshots\ocr_words.json', encoding='utf-8'))
rows = defaultdict(list)
for w in d:
    rows[w['y'] // 20].append(w)

lines = []
for y in sorted(rows):
    seg = ' | '.join(f"{w['text']}@{w['x']},{w['y']}" for w in sorted(rows[y], key=lambda w: w['x']))
    lines.append(f'Y~{y * 20}: {seg}')

out = r'D:\7tan\7tanAI\data\screenshots\layout.txt'
with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('saved', len(lines), 'rows ->', out)
