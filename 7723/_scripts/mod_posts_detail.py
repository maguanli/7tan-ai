# -*- coding: utf-8 -*-
import pickle, re, collections, sys
OUT = r'D:\7tan\7tanAI\7723\_dump'
LT = pickle.load(open(OUT + '_lt.pkl', 'rb'))
HF = pickle.load(open(OUT + '_hf.pkl', 'rb'))
HFI = collections.defaultdict(list)
for h in HF:
    HFI[h[1]].append(h)

def strip_ubb(t):
    if not t:
        return ''
    t = t.replace('\\r', '\n').replace('\\n', '\n')
    t = re.sub(r'（\s*/?\s*(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply|nimg|s|hellos|now)\b[^）]*）', ' ', t, flags=re.I)
    t = re.sub(r'\(/?(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply|nimg|s|hellos|now)\b[^)]*\)', ' ', t, flags=re.I)
    t = re.sub(r'\[/?(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply|nimg|s|hellos|now)\b[^\]]*\]', ' ', t, flags=re.I)
    t = re.sub(r'https?://\S+', ' ', t)
    t = re.sub(r'\\+', '', t)
    return re.sub(r'\s+', ' ', t).strip()

who = sys.argv[1]
out = []
for t in LT:
    if (t[3] or '').strip() == who and (t[7] or '')[:4] <= '2016':
        nr = len([h for h in HFI.get(t[0], []) if h[4] and h[5] and h[5][:4] <= '2016'])
        out.append('[%s|%s] 回复%d 《%s》\n   %s' % (t[0], (t[7] or '')[:10], nr, strip_ubb(t[5]), strip_ubb(t[6])[:160]))
open(r'D:\7tan\7tanAI\7723\_scripts\_one.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('n=', len(out))
