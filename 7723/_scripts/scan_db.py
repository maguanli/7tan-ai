# -*- coding: utf-8 -*-
import os, sqlite3
roots = [r'D:\7tan\7tanAI\data', r'D:\7tan\7tanAI']
seen = set()
out = []
for root in roots:
    for dp, dn, fn in os.walk(root):
        if '.venv' in dp or 'node_modules' in dp or '.git' in dp:
            continue
        for f in fn:
            if f.endswith(('.db', '.sqlite', '.sqlite3')):
                p = os.path.join(dp, f)
                if p in seen:
                    continue
                seen.add(p)
                sz = os.path.getsize(p)
                try:
                    con = sqlite3.connect('file:%s?mode=ro' % p.replace('\\', '/'), uri=True)
                    cur = con.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    ts = [r[0] for r in cur.fetchall()]
                    if ts:
                        out.append('%.1fKB  %s  -> %s' % (sz / 1024, p, ','.join(ts)))
                    con.close()
                except Exception as e:
                    pass
open(r'D:\7tan\7tanAI\7723\_scripts\_dbscan.txt', 'w', encoding='utf-8').write('\n'.join(out))
print(len(out))
