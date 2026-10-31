# -*- coding: utf-8 -*-
"""终检：有回复的帖子 / 回复超过一页的帖子 / 复测冷页"""
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
cur.execute("""
  SELECT t.id, COUNT(h.id) c FROM ll_lt t JOIN ll_lthf h ON h.ll_id=t.id
   WHERE IFNULL(t.ll_or,0)=0 GROUP BY t.id HAVING c BETWEEN 3 AND 15 ORDER BY c DESC LIMIT 1
""")
out['some_replies'] = cur.fetchone()
cur.execute("""
  SELECT t.id, COUNT(h.id) c FROM ll_lt t JOIN ll_lthf h ON h.ll_id=t.id
   WHERE IFNULL(t.ll_or,0)=0 GROUP BY t.id HAVING c > 25 ORDER BY c DESC LIMIT 1
""")
out['many_replies'] = cur.fetchone()
print('JSON=' + json.dumps(out, ensure_ascii=False, default=str))
conn.close()
'''.replace('__PW__', MYC)

p = ROOT / '_srv' / '_probe_edge2.py'
p.write_text(probe, encoding='utf-8')
sftp.put(str(p), '/D:/workspace/ai_poster/_probe_edge2.py')
PYC = r'"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"'
o, e = run(PYC + r' "D:\workspace\ai_poster\_probe_edge2.py"')
line = [l for l in o.split('\n') if l.startswith('JSON=')]
print('[DB]', line[0][5:] if line else (o.strip()[:300] or e.strip()[:300]))
ssh.exec_command(r'del /q "D:\workspace\ai_poster\_probe_edge2.py"')
data = json.loads(line[0][5:]) if line else {}

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36'}


def check(label, pid, replies):
    url = 'https://www.7tan.com/bbs/%d/' % pid
    t0 = time.time()
    html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode('utf-8', 'ignore')
    ms = (time.time() - t0) * 1000
    bad = [b for b in ['Warning:', 'Notice:', 'Fatal error', 'Deprecated:'] if b in html]
    i_load = html.find('id="loadMoreStatus"')
    i_am = html.find('class="author-more"')
    i_box = html.find('<!-- 回复框 -->')
    n_am = len(re.findall(r'class="am-link"', html))
    has_lm = 'load-more-btn' in html
    print('\n[%s] id=%d 回复=%d  %s  %.0fms  %d KB' % (label, pid, replies, url, ms, len(html.encode()) // 1024))
    print('   错误=%s  模块条数=%d  加载更多按钮=%s' % (bad or '无', n_am, has_lm))
    print('   位置 loadMore@%d < author-more@%d < 回复框@%d  -> %s'
          % (i_load, i_am, i_box, i_load < i_am < i_box))
    assert not bad and n_am == 6 and i_load < i_am < i_box


if data.get('some_replies'):
    check('少量回复', data['some_replies'][0], data['some_replies'][1])
if data.get('many_replies'):
    check('多回复(需加载更多)', data['many_replies'][0], data['many_replies'][1])

print('\n[复测] useid=0 的 66205')
t0 = time.time()
html = urllib.request.urlopen(urllib.request.Request('https://www.7tan.com/bbs/66205/', headers=UA), timeout=30).read().decode('utf-8', 'ignore')
print('  %.0fms  模块=%s' % ((time.time() - t0) * 1000, 'class="author-more"' in html))

sftp.close()
ssh.close()
