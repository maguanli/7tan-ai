# -*- coding: utf-8 -*-
"""边界核验：单帖作者 / 高产作者 / 无回复 / 已锁帖"""
import io, json, re, sys, time
import urllib.request
from pathlib import Path
import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(r'D:\7tan\7tanAI')
cfg = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))
srv = cfg['server']
MYC = 'r9wDeVjegCswFuxtmCztzpL3rGay'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
            timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()


def run(cmd, t=180):
    _, o, e = ssh.exec_command(cmd, timeout=t)
    return o.read().decode('utf-8', 'ignore'), e.read().decode('utf-8', 'ignore')


probe = '''# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymysql, json
conn = pymysql.connect(host='127.0.0.1', user='tanapp', password='__PW__',
                       database='7tan_cn', charset='utf8mb4')
cur = conn.cursor()
out = {}
# 只有 1 篇可见帖的作者
cur.execute("""
  SELECT ll_useid, COUNT(*) c, MIN(id) FROM ll_lt
   WHERE IFNULL(ll_or,0)=0 AND ll_useid>0
   GROUP BY ll_useid HAVING c=1 LIMIT 1
""")
out['single'] = cur.fetchone()
# 高产作者的一篇
cur.execute("SELECT id FROM ll_lt WHERE ll_useid=99901 AND IFNULL(ll_or,0)=0 ORDER BY id DESC LIMIT 1")
out['top_uid99901'] = cur.fetchone()
# 锁帖
cur.execute("SELECT id FROM ll_lt WHERE ll_lock=1 AND IFNULL(ll_or,0)=0 ORDER BY id DESC LIMIT 1")
out['locked'] = cur.fetchone()
# 匿名/useid=0 的帖
cur.execute("SELECT id FROM ll_lt WHERE ll_useid=0 AND IFNULL(ll_or,0)=0 ORDER BY id DESC LIMIT 1")
out['anon'] = cur.fetchone()
print('JSON=' + json.dumps(out, ensure_ascii=False, default=str))
conn.close()
'''.replace('__PW__', MYC)

p = ROOT / '_srv' / '_probe_edge.py'
p.write_text(probe, encoding='utf-8')
sftp.put(str(p), '/D:/workspace/ai_poster/_probe_edge.py')
PYC = r'"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"'
o, e = run(PYC + r' "D:\workspace\ai_poster\_probe_edge.py"')
line = [l for l in o.split('\n') if l.startswith('JSON=')]
print('[DB]', line[0][5:] if line else (o.strip()[:300] or e.strip()[:300]))
ssh.exec_command(r'del /q "D:\workspace\ai_poster\_probe_edge.py"')
data = json.loads(line[0][5:]) if line else {}

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36'}


def check(label, pid):
    if not pid:
        print('\n[%s] 无样本，跳过' % label)
        return
    url = 'https://www.7tan.com/bbs/%d/' % pid
    t0 = time.time()
    html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode('utf-8', 'ignore')
    ms = (time.time() - t0) * 1000
    bad = [b for b in ['Warning:', 'Notice:', 'Fatal error', 'Deprecated:'] if b in html]
    has = 'class="author-more"' in html
    n = len(re.findall(r'class="am-link"', html))
    head = re.search(r'<h3 class="am-title">(.*?)</h3>', html, re.S)
    print('\n[%s] %s  %.0fms  %d KB  错误=%s  模块=%s  条数=%d  标题=%s'
          % (label, url, ms, len(html.encode()) // 1024, bad or '无', has, n,
             re.sub(r'<[^>]+>', '', head.group(1)) if head else '-'))
    if has:
        items = re.findall(r'<a class="am-link" href="([^"]+)">([^<]+)</a>', html)
        for u, t in items[:3]:
            print('     %s  %s' % (u, t[:30]))
    return has


if data.get('single'):
    check('单帖作者', data['single'][2])
if data.get('top_uid99901'):
    check('高产作者99901', data['top_uid99901'][0])
if data.get('locked'):
    check('锁帖', data['locked'][0])
if data.get('anon'):
    check('useid=0', data['anon'][0])

sftp.close()
ssh.close()
