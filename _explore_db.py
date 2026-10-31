# -*- coding: utf-8 -*-
"""探查 5：DB 结构 + uid=1 的发帖情况（决定推荐栏取数策略）"""
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
conn = pymysql.connect(host='127.0.0.1', user='tanapp', password='%s',
                       database='7tan_cn', charset='utf8mb4')
cur = conn.cursor()
print('--- ll_lt 列 ---')
cur.execute("SHOW COLUMNS FROM ll_lt")
cols = [r[0] for r in cur.fetchall()]
print(', '.join(cols))
print()
print('--- ll_lt 行数 / 各作者 ---')
cur.execute("SELECT COUNT(*) FROM ll_lt WHERE ll_or IN (0,1) OR ll_or IS NULL")
print('visible posts =', cur.fetchone()[0])
cur.execute("SELECT ll_useid, COUNT(*) c FROM ll_lt WHERE (ll_or IN (0,1) OR ll_or IS NULL) GROUP BY ll_useid ORDER BY c DESC LIMIT 8")
print('top authors (useid, count) =', cur.fetchall())
print()
print('--- uid=1 近期帖 ---')
cur.execute("SELECT id, ll_idd, ll_or, ll_rc, ll_time1, LEFT(ll_biaoti,42) FROM ll_lt WHERE ll_useid=1 ORDER BY id DESC LIMIT 15")
for r in cur.fetchall():
    print(r)
print()
print('--- uid=1 总数 ---')
cur.execute("SELECT COUNT(*) FROM ll_lt WHERE ll_useid=1")
print('total =', cur.fetchone()[0])
print()
print('--- 84008 归属 ---')
cur.execute("SELECT id, ll_useid, ll_idd, ll_or, LEFT(ll_biaoti,30) FROM ll_lt WHERE id=84008")
print(cur.fetchone())
print()
print('--- 昵称 ---')
cur.execute("SELECT id, ll_name, ll_n_name FROM ll_useregs WHERE id=1")
print(cur.fetchall())
conn.close()
''' % MYC

local = Path(r'D:\7tan\7tanAI\_srv\_probe_author.py')
local.write_text(probe, encoding='utf-8')
remote = '/D:/workspace/ai_poster/_probe_author.py'
sftp.put(str(local), remote)

PYC = r'"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"'
cmd = PYC + r' "D:\workspace\ai_poster\_probe_author.py"'
_, o, e = ssh.exec_command(cmd, timeout=120)
print(o.read().decode('utf-8', 'ignore'))
err = e.read().decode('utf-8', 'ignore')
if err.strip():
    print('[stderr]', err[:1500])

ssh.exec_command(r'del /q "D:\workspace\ai_poster\_probe_author.py"')
sftp.close()
ssh.close()
