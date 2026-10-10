# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

p = r'D:\7tan\7tan_cn_20260515_090725.sql'
with open(p, 'r', encoding='utf-16', errors='ignore') as f:
    data = f.read()

# 抓取某张表的 CREATE 语句，看字段
def show_schema(tname):
    m = re.search(r'CREATE TABLE `'+re.escape(tname)+r'` \((.*?)\n\) ENGINE', data, re.S)
    if not m:
        m = re.search(r'CREATE TABLE `'+re.escape(tname)+r'` \((.*?)\);', data, re.S)
    if m:
        print(f'\n=== SCHEMA {tname} ===')
        for line in m.group(1).split('\n'):
            line=line.strip()
            if line.startswith('`') or line.startswith('PRIMARY') or line.startswith('KEY'):
                print(line)
    else:
        print(f'\n[!] schema not found for {tname}')

for t in ['ll_lt','ll_lthf','ll_ltbz','ll_ltpl','ll_users','ll_lt_bankuai','ll_ltzt']:
    show_schema(t)
