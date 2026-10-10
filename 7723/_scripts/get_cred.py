# -*- coding: utf-8 -*-
import sqlite3, sys, os, json
sys.path.insert(0, r'D:\7tan\7tanAI')
os.chdir(r'D:\7tan\7tanAI')
db = r'D:\7tan\7tanAI\data\7tan.db'
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
out = ['TABLES: ' + ', '.join(tables)]
for t in tables:
    if 'site' in t.lower() or 'cred' in t.lower() or 'acc' in t.lower():
        try:
            cur.execute('SELECT * FROM "%s" LIMIT 20' % t)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            out.append('\n== %s == cols=%s' % (t, cols))
            for r in rows:
                out.append(repr(r))
        except Exception as e:
            out.append('ERR ' + str(e))
open(r'D:\7tan\7tanAI\7723\_scripts\_cred.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('ok')
