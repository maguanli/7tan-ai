# -*- coding: utf-8 -*-
"""从 _dump_lt.pkl 中为每位版主找出其代表帖 -> 输出 JSON"""
import pickle, json, re, collections

OUT = r'D:\7tan\7tanAI\7723\_dump'
LT = pickle.load(open(OUT + '_lt.pkl', 'rb'))
HF = pickle.load(open(OUT + '_hf.pkl', 'rb'))

HFI = collections.defaultdict(list)
for h in HF:
    HFI[h[1]].append(h)

# 作者字段索引 3；标题 5；正文 6；日期 7
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

# 统计所有作者
authors = collections.Counter()
for t in LT:
    a = (t[3] or '').strip()
    if a:
        authors[a] += 1

print('unique authors:', len(authors))
print('total posts:', len(LT))

# 输出前 300 名作者，供核对
with open(r'D:\7tan\7tanAI\7723\_scripts\_authors.txt', 'w', encoding='utf-8') as f:
    for a, c in authors.most_common(400):
        f.write('%s\t%d\n' % (a, c))
print('top authors written')

# 限定年份 <= 2016 且作者非空
def y2016(dt):
    return dt and dt[:4] <= '2016'

# 打印若干已知版主的发帖数
KEY = ['存我', '月下', '沈星辰', '邪、苍', '皇甫朝云', '小殇', '蛋定', '徐良',
       '沉默', '大门', '莫小跳', '博丽灵梦', '清风明月', 'Slience', 'Silence',
       '小太刀', 'BLOOD', '秋韵物语', '小基', '流殇', '陌生人', '灰烬',
       '田驰', '叶繁成花', '穆清', '莽蛋', '月光', '苏小染', '触屏', '残刃',
       '不修', '浅', '咸蛋超人', '凉宫']
print('\n--- 关键词命中作者 ---')
for k in KEY:
    hits = [(a, c) for a, c in authors.items() if k in a]
    hits.sort(key=lambda x: -x[1])
    print(k, '->', hits[:6])

print('\n--- 作者样例（前30）---')
for a, c in authors.most_common(30):
    print(repr(a), c)
