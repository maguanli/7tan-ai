# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

p = r'D:\7tan\7tan_cn_20260515_090725.sql'

# 先判断编码：看开头
with open(p, 'rb') as f:
    head = f.read(4)
print('head:', head)

# mysqldump 一般是 utf-8；try utf-8 first
encodings = ['utf-8', 'utf-16', 'gbk', 'latin-1']
text_head = None
for enc in encodings:
    try:
        with open(p, 'r', encoding=enc, errors='strict') as f:
            chunk = f.read(200000)
        print(f'OK decode with {enc}, first 300 chars:')
        print(chunk[:300])
        text_head = chunk
        break
    except Exception as e:
        print(f'fail {enc}: {e}')
