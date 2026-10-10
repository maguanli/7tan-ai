# -*- coding: utf-8 -*-
import pickle, collections
OUT = r'D:\7tan\7tanAI\7723\_dump'
LT = pickle.load(open(OUT + '_lt.pkl', 'rb'))
authors = collections.Counter()
for t in LT:
    a = (t[3] or '').strip()
    if a:
        authors[a] += 1
al = sorted(authors.items(), key=lambda x: -x[1])
KEYS = ['月', '星辰', '徐', '托尼', '触屏', '沉默', '葬忆', '神月', '淡然', '浅']
lines = []
for k in KEYS:
    hits = [(a, c) for a, c in al if k in a][:25]
    lines.append('%s => %s' % (k, ' ｜ '.join('%s(%d)' % (a, c) for a, c in hits)))
open(r'D:\7tan\7tanAI\7723\_scripts\_find2.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('ok')
