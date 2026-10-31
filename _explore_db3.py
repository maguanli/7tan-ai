# -*- coding: utf-8 -*-
"""探查 8：ll_lt 索引（判断按作者取数是否走索引）"""
import io, json, sys
from pathlib import Path
import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

cfg = json.loads((Path(r'D:\7tan\7tanAI') / 'config' / 'deploy.json').read_text(encoding='utf-8'))
srv = cfg['server']
MYC = 'r9wDeVjegCswFuxtmCztzpL3rGay'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
            timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

probe = '''# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymysql
conn = pymysql.connect(host='127.0.0.1', user='tanapp', password='__PW__',
                       database='7tan_cn', charset='utf8mb4')
cur = conn.cursor()
cur.execute("SHOW INDEX FROM ll_lt")
rows = cur.fetchall()
idx = {}
for r in rows:
    idx.setdefault(r[2], []).append(r[4])
for k, v in idx.items():
    print('  %-24s %s' % (k, v))
print()
print('[EXPLAIN 推荐位查询]')
cur.execute("""
EXPLAIN SELECT t.id FROM ll_lt t
 WHERE t.ll_useid=1 AND t.id<>84008 AND IFNULL(t.ll_or,0)=0
 ORDER BY (t.ll_idd=18) DESC, t.id DESC LIMIT 6
""")
for r in cur.fetchall():
    print('  ', r[:8])
print()
print('[实测耗时]')
import time
t0=time.time()
for _ in range(5):
    cur.execute("""
    SELECT t.id, t.ll_biaoti, t.ll_idd, IFNULL(t.ll_rc,0), DATE_FORMAT(t.ll_time1,'%Y-%m-%d')
      FROM ll_lt t
     WHERE t.ll_useid=1 AND t.id<>84008 AND IFNULL(t.ll_or,0)=0
     ORDER BY (t.ll_idd=18) DESC, t.id DESC LIMIT 6
    """)
    cur.fetchall()
print('  5 次查询 %.1f ms' % ((time.time()-t0)*1000))
conn.close()
'''.replace('__PW__', MYC)

local = Path(r'D:\7tan\7tanAI\_srv\_probe3.py')
local.write_text(probe, encoding='utf-8')
sftp.put(str(local), '/D:/workspace/ai_poster/_probe3.py')

PYC = r'"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"'
_, o, e = ssh.exec_command(PYC + r' "D:\workspace\ai_poster\_probe3.py"', timeout=120)
print(o.read().decode('utf-8', 'ignore'))
err = e.read().decode('utf-8', 'ignore')
if err.strip():
    print('[stderr]', err[:800])

ssh.exec_command(r'del /q "D:\workspace\ai_poster\_probe3.py"')
sftp.close()
ssh.close()
