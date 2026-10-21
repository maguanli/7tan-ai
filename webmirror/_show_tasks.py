import json, io, sys
sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\7tan\7tanAI\webmirror\downloads\_tasks.json'
d = json.load(open(p, encoding='utf-8'))
print('total tasks:', len(d))
for i, t in enumerate(d):
    print(i, t.get('id'), '| max_pages =', t.get('config', {}).get('max_pages'), '| status =', t.get('status'), '| start =', t.get('start_url'))
    if t.get('id') == '20261011-063926-4ba5eb':
        print('   >>> TARGET FOUND idx=', i, 'max_pages=', t['config'].get('max_pages'))
        print('   >>> keys:', list(t.keys()))
