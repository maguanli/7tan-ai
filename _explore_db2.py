# -*- coding: utf-8 -*-
"""探查 7：ll_or / ll_hide 取值分布 + 84008 推荐位预览"""
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

print('[ll_or 分布]')
cur.execute("SELECT ll_or, COUNT(*) FROM ll_lt GROUP BY ll_or ORDER BY 2 DESC")
print(cur.fetchall())

print('[ll_hide 分布]')
cur.execute("SELECT ll_hide, COUNT(*) FROM ll_lt GROUP BY ll_hide ORDER BY 2 DESC")
print(cur.fetchall())

print('[uid=1 按板块]')
cur.execute("SELECT ll_idd, COUNT(*) FROM ll_lt WHERE ll_useid=1 AND IFNULL(ll_or,0)=0 GROUP BY ll_idd ORDER BY 2 DESC")
print(cur.fetchall())

print('[84008 推荐位预览：同板块优先，取6条]')
cur.execute("""
    SELECT t.id, t.ll_idd, IFNULL(t.ll_rc,0) AS v, DATE_FORMAT(t.ll_time1,'%%Y-%%m-%%d') AS d,
           LEFT(t.ll_biaoti, 40) AS bt
    FROM ll_lt t
    WHERE t.ll_useid=1 AND t.id<>84008 AND IFNULL(t.ll_or,0)=0
    ORDER BY (t.ll_idd=18) DESC, t.id DESC
    LIMIT 8
""")
for r in cur.fetchall():
    print('  ', r)

print('[不排除当前帖的写法会怎样 —— 检查是否有同作者多帖重复]')
cur.execute("SELECT COUNT(*) FROM ll_lt WHERE ll_useid=1 AND IFNULL(ll_or,0)=0")
print('uid=1 可见帖 =', cur.fetchone()[0])
conn.close()
'''.replace('__PW__', MYC)

local = Path(r'D:\7tan\7tanAI\_srv\_probe2.py')
local.write_text(probe, encoding='utf-8')
sftp.put(str(local), '/D:/workspace/ai_poster/_probe2.py')

PYC = r'"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"'
_, o, e = ssh.exec_command(PYC + r' "D:\workspace\ai_poster\_probe2.py"', timeout=120)
print(o.read().decode('utf-8', 'ignore'))
err = e.read().decode('utf-8', 'ignore')
if err.strip():
    print('[stderr]', err[:800])

ssh.exec_command(r'del /q "D:\workspace\ai_poster\_probe2.py"')
sftp.close()
ssh.close()
