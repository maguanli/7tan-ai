# -*- coding: utf-8 -*-
import pickle, re, collections
OUT = r'D:\7tan\7tanAI\7723\_dump'
LT = pickle.load(open(OUT + '_lt.pkl', 'rb'))
HF = pickle.load(open(OUT + '_hf.pkl', 'rb'))

tags = collections.Counter()
text = []
for t in LT:
    if t[6]:
        text.append(t[6])
for h in HF:
    if h[4]:
        text.append(h[4])
blob = '\n'.join(text)

# 统计各类标签出现
pats = [r'\(url=', r'\[url=', r'\(/url\)', r'\[/url\]', r'\(img', r'\[img',
        r'\(b\)', r'\[b\]', r'\(color', r'\[color', r'\(size', r'\[size',
        r'\(center', r'\[center', r'\(quote', r'\[quote', r'\(hide', r'\[hide',
        r'\(title', r'\[title', r'\(note', r'\[note', r'\(reply', r'\[reply']
res = []
for p in pats:
    res.append('%s : %d' % (p, len(re.findall(p, blob, flags=re.I))))

# 统计所有 （xxx 或 (xxx 形式的标签名
alltags = collections.Counter(re.findall(r'[\(（]\s*/?\s*([a-zA-Z]{1,12})\s*[\)）]', blob))
alltags2 = collections.Counter(re.findall(r'[\(（]\s*/?\s*([a-zA-Z]{1,12})\s*=', blob))
open(r'D:\7tan\7tanAI\7723\_scripts\_ubbscan.txt', 'w', encoding='utf-8').write(
    '\n'.join(res) + '\n\n-- 圆括号标签 --\n' +
    '\n'.join('%s %d' % (k, v) for k, v in alltags.most_common(40)) +
    '\n\n-- 圆括号带=标签 --\n' +
    '\n'.join('%s %d' % (k, v) for k, v in alltags2.most_common(40)))
print('ok')
