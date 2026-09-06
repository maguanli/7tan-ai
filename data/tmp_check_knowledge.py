# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = r'D:\7tan\7tanAI\data\tan_model_memory.json'
with open(path, 'r', encoding='utf-8') as f:
    d = json.load(f)

print('=== knowledge (%d 条) ===' % len(d.get('knowledge', [])))
for i, k in enumerate(d.get('knowledge', [])):
    print('[%d] key=%r' % (i, k.get('key')))
    print('    content=%r' % (k.get('content', '')[:500]))
    print('    source=%r confidence=%r ts=%r' % (k.get('source'), k.get('confidence'), k.get('ts')))
