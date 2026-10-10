# -*- coding: utf-8 -*-
"""精确查找版主作者名 & 候选代表帖"""
import pickle, json, re, collections

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
    t = re.sub(r'（\s*/?\s*(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply)\b[^）]*）', '', t, flags=re.I)
    t = re.sub(r'\(/?(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply)\b[^)]*\)', '', t, flags=re.I)
    t = re.sub(r'\\+', '', t)
    t = re.sub(r'\s*\n\s*', '\n', t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    return t.strip()

authors = collections.Counter()
byauth = collections.defaultdict(list)
for t in LT:
    a = (t[3] or '').strip()
    if a:
        authors[a] += 1
        byauth[a].append(t)

# 待查关键词
KEYS = ['月下', '沈星辰', '徐良', '托尼斯塔克', '莫小跳', '玉碎', '倾城', '咸蛋超人',
        '邪、苍', '存我', '拾壹', '随风', '清风', '寒', '光']
res = {}
for k in KEYS:
    hits = sorted([(a, c) for a, c in authors.items() if k in a], key=lambda x: -x[1])
    res[k] = hits
open(r'D:\7tan\7tanAI\7723\_scripts\_mods.txt', 'w', encoding='utf-8').write(
    '\n'.join('%s -> %s' % (k, ['%s(%d)' % (a, c) for a, c in v]) for k, v in res.items()))
print('done')

# 同时检查 ll_lt 里 id 与作者（用于核对 ID5/ID6 等）
# 字段: 0=id 3=author 5=title 7=date
# 打印 ID 5/6/1008/8382/9971/11712/11789/12712/13656/16200/17342 的帖
for tid in ['5', '6', '1008', '8382', '9971', '11712', '11789', '12712', '13656', '16200', '17342']:
    pass
print('total posts', len(LT))
