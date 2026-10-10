# -*- coding: utf-8 -*-
"""从主站 mysqldump(utf-16) 还原老 7723 论坛数据 -> pickle
用法: python extract.py"""
import re, pickle

P = r'D:\7tan\7tan_cn_20260515_090725.sql'
OUT = r'D:\7tan\7tanAI\7723\_dump'


def parse_values(s):
    rows, i, n = [], 0, len(s)
    ESC = {'n': '\n', 'r': '\r', 't': '\t', '0': '\0', '\\': '\\',
           "'": "'", '"': '"', 'Z': '\x1a', 'b': '\b', 'f': '\f'}
    while i < n:
        while i < n and s[i] in ' \r\n\t,':
            i += 1
        if i >= n or s[i] != '(':
            break
        i += 1
        row = []
        while i < n:
            while i < n and s[i] in ' \r\n\t':
                i += 1
            if i < n and s[i] == ')':
                i += 1
                break
            if i < n and s[i] == "'":
                i += 1
                buf = []
                while i < n:
                    c = s[i]
                    if c == '\\' and i + 1 < n:
                        buf.append(ESC.get(s[i + 1], s[i + 1])); i += 2
                    elif c == "'":
                        i += 1; break
                    else:
                        buf.append(c); i += 1
                row.append(''.join(buf))
            else:
                j = i
                while j < n and s[j] not in ',)':
                    j += 1
                tok = s[i:j].strip(); i = j
                row.append(None if tok.upper() == 'NULL' else tok)
            while i < n and s[i] in ' \r\n\t':
                i += 1
            if i < n and s[i] == ',':
                i += 1; continue
            if i < n and s[i] == ')':
                i += 1; break
        rows.append(row)
    return rows


targets = {'ll_lt', 'll_lthf', 'll_lt_bankuai', 'll_ltbz', 'll_ltzt'}
got = {t: 0 for t in targets}
LT, HF, BK, BZ, ZT = [], [], [], [], []
with open(P, 'r', encoding='utf-16', errors='ignore') as f:
    for line in f:
        if not line.startswith('INSERT INTO'):
            continue
        m = re.match(r'INSERT INTO `([^`]+)` VALUES (.*)', line.rstrip('\n'))
        if not m or m.group(1) not in targets:
            continue
        t, rows = m.group(1), parse_values(m.group(2))
        got[t] += len(rows)
        if t == 'll_lt':
            for r in rows:
                r = r + [None] * (34 - len(r))
                LT.append([r[0], r[1], r[2], r[3], r[4], r[5], (r[6] or '')[:4000],
                           r[18], r[12], r[13], r[30], r[31]])
        elif t == 'll_lthf':
            for r in rows:
                r = r + [None] * (20 - len(r))
                HF.append([r[0], r[1], r[3], r[6], (r[7] or '')[:1500], r[9]])
        elif t == 'll_lt_bankuai':
            for r in rows:
                BK.append([r[0], r[1], r[2], (r[7] or '')[:500]])
        elif t == 'll_ltbz':
            for r in rows:
                BZ.append(r[:5])
        else:
            ZT.append(r[:9])

print('counts:', got)
pickle.dump(LT, open(OUT + '_lt.pkl', 'wb'))
pickle.dump(HF, open(OUT + '_hf.pkl', 'wb'))
pickle.dump({'BK': BK, 'BZ': BZ, 'ZT': ZT}, open(OUT + '_meta.pkl', 'wb'))
print('saved pickle:', len(LT), len(HF), len(BK), len(BZ))
