# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

p = r'D:\7tan\7tan_cn_20260515_090725.sql'
with open(p, 'r', encoding='utf-16', errors='ignore') as f:
    data = f.read()

for t in ['ll_lt_bankuai','ll_ltzt','ll_ltbz']:
    idx = data.find("INSERT INTO `%s`"%t)
    print(f'\n===== {t} @ {idx} =====')
    if idx>=0:
        print(repr(data[idx:idx+800]))
