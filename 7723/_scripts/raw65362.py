# -*- coding: utf-8 -*-
import pickle
OUT = r'D:\7tan\7tanAI\7723\_dump'
LT = pickle.load(open(OUT + '_lt.pkl', 'rb'))
buf = []
for t in LT:
    if str(t[0]) in ('65362', '55149', '28504', '70379'):
        buf.append('=== id=%s author=%s date=%s title=%s ===' % (t[0], t[3], t[7], t[5]))
        buf.append(repr(t[6])[:1500])
        buf.append('')
open(r'D:\7tan\7tanAI\7723\_scripts\_raw.txt', 'w', encoding='utf-8').write('\n'.join(buf))
print('ok')
