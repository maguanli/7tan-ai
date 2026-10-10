# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

p = r'D:\7tan\7tan_cn_20260515_090725.sql'

# 全量读入（256MB 用 utf-16 解码约 128MB 字符）
with open(p, 'r', encoding='utf-16', errors='ignore') as f:
    data = f.read()
print('total chars:', len(data))

# 找所有 CREATE TABLE
tables = re.findall(r'CREATE TABLE `([^`]+)`', data)
print('table count:', len(tables))
for t in tables:
    print(' -', t)

print('---INSERT counts---')
ins = re.findall(r"INSERT INTO `([^`]+)`", data)
from collections import Counter
c = Counter(ins)
for k, v in c.most_common():
    print(f'{k}: {v}')
