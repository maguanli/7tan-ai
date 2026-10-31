# -*- coding: utf-8 -*-
"""收尾：删远端临时文件 + 删本地一次性脚本 + 最终连通性复查"""
import io, json, sys, re, urllib.request
from pathlib import Path
import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(r'D:\7tan\7tanAI')
cfg = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))
srv = cfg['server']

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
            timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

# 远端临时文件
try:
    sftp.remove('/D:/temp/profile.new.php')
    print('[1] 已删远端 D:/temp/profile.new.php')
except Exception as ex:
    print('[1] 远端临时文件:', ex)

# 远端备份清单
baks = sorted(a.filename for a in sftp.listdir_attr('/D:/workspace/7tan/bbs')
              if a.filename.startswith('profile.php'))
print('[2] bbs 下 profile.php* :', baks)

# live 文件终态
live = sftp.open('/D:/workspace/7tan/bbs/profile.php').read()
print('[3] live 终态 %d B  CRLF=%d' % (len(live), live.count(b'\r\n')))

sftp.close()
ssh.close()

# 本地一次性脚本清理
junk = ['_probe_route.py', '_probe_route2.py', '_probe_route3.py', '_probe_route4.py',
        '_probe_route5.py', '_probe_env.py', '_probe_router.py', '_q_profile.py',
        '_q_boundary.py', '_q_nullcheck.py', '_q_null2.py', '_q_authormore_null.py',
        '_lint_new_profile.py', '_shot_profile2.py',
        '_srv/_smoke_pager.php', '_srv/router.php']
for j in junk:
    p = ROOT / j
    if p.exists():
        p.unlink()
        print('[4] 删除', j)

print('\n[5] 保留:')
for n in ('_dl_profile.py', '_patch_profile_paged.py', '_deploy_profile_paged.py',
          '_verify_profile_paged.py', '_run_on_srv.py', '_shot_profile.py',
          '_srv/profile.remote.php', '_srv/profile.new.php',
          '_srv/profile.php'):
    p = ROOT / n
    print('   %-30s %s' % (n, ('%d B' % p.stat().st_size) if p.exists() else '缺失'))

# 最终连通性
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'
print('\n[6] 相关页面复查:')
for path in ('/bbs/user/1/', '/bbs/user/1/?page=2', '/bbs/84008/', '/bbs/board/18/', '/'):
    req = urllib.request.Request('https://www.7tan.com' + path, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        html = r.read().decode('utf-8', 'ignore')
    errs = sum(html.count(k) for k in ('Warning:', 'Notice:', 'Fatal error', 'Deprecated:'))
    print('   %-24s %s  %6d B  告警=%d' % (path, r.status, len(html), errs))
