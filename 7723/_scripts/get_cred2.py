# -*- coding: utf-8 -*-
import sqlite3, sys, os, json
sys.path.insert(0, r'D:\7tan\7tanAI')
os.chdir(r'D:\7tan\7tanAI')
db = r'D:\7tan\7tanAI\data\games.db'
con = sqlite3.connect(db)
cur = con.cursor()
out = []
for t in ['site_credentials', 'source_sites', 'app_settings']:
    cur.execute('SELECT * FROM "%s" LIMIT 50' % t)
    cols = [d[0] for d in cur.description]
    out.append('== %s == cols=%s' % (t, cols))
    for r in cur.fetchall():
        out.append(repr(r))
    out.append('')
# 尝试解密
try:
    from src.database.db import decrypt_password
    cur.execute('SELECT * FROM site_credentials')
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        out.append('DECRYPT: ' + repr(d))
        for k in d:
            if isinstance(d[k], str) and d[k] and ('pass' in k.lower() or 'pwd' in k.lower() or 'secret' in k.lower() or 'token' in k.lower()):
                try:
                    out.append('   %s -> %s' % (k, decrypt_password(d[k])))
                except Exception as e:
                    out.append('   %s ERR %s' % (k, e))
except Exception as e:
    out.append('IMPORT ERR: ' + str(e))
open(r'D:\7tan\7tanAI\7723\_scripts\_cred2.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('ok')
