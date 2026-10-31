# -*- coding: utf-8 -*-
"""修正上传换行：上一版 write_text 在 Windows 下把 LF 转成了 CRLF。
本脚本重写为 LF、校验字节一致，然后继续补索引 + 清缓存 + 线上核验。
"""
import io, json, sys, time
from pathlib import Path
import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(r'D:\7tan\7tanAI')
cfg = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))
srv = cfg['server']
MYC = 'r9wDeVjegCswFuxtmCztzpL3rGay'
PHP = r'D:\php\php-8.2.35\php.exe'
LOCAL_VIEW = ROOT / '_srv' / 'view.php'

# 从已生成的 patched 文本重建（_srv/view.php.new 内容正确，只是磁盘换行被转了）
patched_text = (ROOT / '_srv' / 'view.php.new').read_text(encoding='utf-8')
orig_text = LOCAL_VIEW.read_text(encoding='utf-8')
print('[0] patched %d 字符 / 原始 %d 字符' % (len(patched_text), len(orig_text)))
assert patched_text.count('class="author-more"') == 1, 'author-more 容器数异常'
assert orig_text.count('author-more') == 0, '原始文件已含 author-more'
print('[0] author-more 出现次数 = %d（CSS 选择器 + 容器各一次）' % patched_text.count('author-more'))
assert patched_text.count('<!-- 回复框 -->') == 1

# 关键：LF 原样落盘
out = ROOT / '_srv' / 'view.php.lf'
with open(out, 'wb') as f:
    f.write(patched_text.encode('utf-8'))
raw = out.read_bytes()
print('[0] LF 落盘 %d bytes，CR 数 = %d（应为 0）' % (len(raw), raw.count(b'\r')))
assert raw.count(b'\r') == 0, '仍含 CR'

# 原始文件是否为 LF（用来确认站点自身习惯）
orig_raw = None
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
            timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()


def run(cmd, t=180):
    _, o, e = ssh.exec_command(cmd, timeout=t)
    return o.read().decode('utf-8', 'ignore'), e.read().decode('utf-8', 'ignore')


# 从备份取原文，确认原来是 LF
bak = sorted([a.filename for a in sftp.listdir_attr('/D:/workspace/7tan/bbs')
              if a.filename.startswith('view.php.bak_authormore_')])
print('[1] 备份文件:', bak)
btxt = sftp.open('/D:/workspace/7tan/bbs/' + bak[-1]).read()
print('[1] 备份 bytes=%d  CR=%d  （原文件换行风格）' % (len(btxt), btxt.count(b'\r')))

# 语法检查（非 web 目录）
sftp.put(str(out), '/D:/workspace/ai_poster/view_lf_check.php')
o, e = run('"%s" -l "D:\\workspace\\ai_poster\\view_lf_check.php"' % PHP)
print('[2] php -l:', (o.strip() or e.strip())[:200])
assert 'No syntax errors' in o

# 覆盖
sftp.put(str(out), '/D:/workspace/7tan/bbs/view.php')
st = sftp.stat('/D:/workspace/7tan/bbs/view.php')
print('[3] 覆盖后 %d bytes，期望 %d' % (st.st_size, len(raw)))
assert st.st_size == len(raw), '大小仍不一致'

# 回读比对
back = sftp.open('/D:/workspace/7tan/bbs/view.php').read()
print('[3] 回读一致 =', back == raw, ' CR=%d' % back.count(b'\r'))
assert back == raw, '回读不一致'

ssh.exec_command(r'del /q "D:\workspace\ai_poster\view_lf_check.php"')

# ---------- 索引 ----------
probe = '''# -*- coding: utf-8 -*-
import io, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymysql
conn = pymysql.connect(host='127.0.0.1', user='tanapp', password='__PW__',
                       database='7tan_cn', charset='utf8mb4', autocommit=True)
cur = conn.cursor()
cur.execute("SHOW INDEX FROM ll_lt")
names = set(r[2] for r in cur.fetchall())
if 'idx_ll_useid_id' in names:
    print('IDX=exists')
else:
    t0 = time.time()
    cur.execute("ALTER TABLE ll_lt ADD INDEX idx_ll_useid_id (ll_useid, id)")
    print('IDX=created %.2fs' % (time.time() - t0))
cur.execute("SHOW INDEX FROM ll_lt")
print('IDX_NOW=', 'idx_ll_useid_id' in set(r[2] for r in cur.fetchall()))
cur.execute("""
EXPLAIN SELECT t.id FROM ll_lt t
 WHERE t.ll_useid=1 AND t.id<>84008 AND IFNULL(t.ll_or,0)=0
 ORDER BY (t.ll_idd=18) DESC, t.id DESC LIMIT 6
""")
r = cur.fetchone()
print('PLAN table=%s type=%s key=%s rows=%s extra=%s' % (r[2], r[3], r[5], r[9], r[10]))
t0 = time.time()
for _ in range(20):
    cur.execute("""
    SELECT t.id, t.ll_biaoti, t.ll_idd, IFNULL(t.ll_rc,0), DATE_FORMAT(t.ll_time1,'%Y-%m-%d'), c.ll_title
      FROM ll_lt t LEFT JOIN ll_class c ON t.ll_idd=c.id
     WHERE t.ll_useid=1 AND t.id<>84008 AND IFNULL(t.ll_or,0)=0
     ORDER BY (t.ll_idd=18) DESC, t.id DESC LIMIT 6
    """)
    cur.fetchall()
print('PERF=20 次 %.1f ms' % ((time.time()-t0)*1000))
conn.close()
'''.replace('__PW__', MYC)

p = ROOT / '_srv' / '_add_index2.py'
p.write_text(probe, encoding='utf-8')
sftp.put(str(p), '/D:/workspace/ai_poster/_add_index2.py')
PYC = r'"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"'
o, e = run(PYC + r' "D:\workspace\ai_poster\_add_index2.py"')
print('[4] 索引:', (o.strip() or e.strip())[:600])
assert 'IDX_NOW= True' in o, '索引创建失败'
ssh.exec_command(r'del /q "D:\workspace\ai_poster\_add_index2.py"')

# ---------- 清缓存 ----------
files = sftp.listdir('/D:/workspace/7tan/cache/topic')
for pid in [84008, 84023, 83954, 83897]:
    hit = [f for f in files if f.startswith(str(pid) + '_')]
    for f in hit:
        sftp.remove('/D:/workspace/7tan/cache/topic/' + f)
    print('[5] 缓存 %d 清除 %d 个 %s' % (pid, len(hit), hit))

sftp.close()
ssh.close()
print('\n[OK]')
