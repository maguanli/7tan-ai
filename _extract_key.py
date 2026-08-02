# -*- coding: utf-8 -*-
content = open(r'D:\7tan\7tanAI\_audit_result.txt', encoding='utf-8').read()
lines = content.split('\n')
start = False
for i, l in enumerate(lines):
    if '[2]' in l:
        start = True
    if start:
        print(l)
