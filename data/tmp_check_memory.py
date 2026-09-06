# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = r'D:\7tan\7tanAI\data\tan_model_memory.json'
with open(path, 'r', encoding='utf-8') as f:
    d = json.load(f)

print('top type:', type(d).__name__)
if isinstance(d, dict):
    print('top keys:', list(d.keys()))
    for k, v in d.items():
        if isinstance(v, list):
            print('  list[%s] len=%d' % (k, len(v)))
            if v and isinstance(v[0], dict):
                print('    sample keys:', list(v[0].keys()))
        elif isinstance(v, dict):
            print('  dict[%s] len=%d' % (k, len(v)))
        else:
            print('  scalar[%s] = %r' % (k, str(v)[:100]))
