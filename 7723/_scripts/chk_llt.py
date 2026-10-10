# -*- coding: utf-8 -*-
import io, re, sys
path = r'D:\7tan\7tan_cn_20260515_090725.sql'
buf = []
grab = False
with io.open(path, encoding='utf-16', errors='ignore') as f:
    for line in f:
        if not grab and re.search(r'CREATE TABLE `ll_lt`', line):
            grab = True
        if grab:
            buf.append(line.rstrip('\n'))
            if line.rstrip().endswith(';'):
                break
print('\n'.join(buf)[:4000])
