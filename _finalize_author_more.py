# -*- coding: utf-8 -*-
"""收尾：确认远端文件首尾完整 + 统计改动 + 清理一次性脚本"""
import io, json, sys
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

remote = '/D:/workspace/7tan/bbs/view.php'
f = sftp.open(remote)
raw = f.read().decode('utf-8', 'ignore')
f.close()

lines = raw.split('\r\n')
print('[1] 远端 view.php 行数 =', len(lines), ' CR =', raw.count('\r'), ' 字节 =', len(raw.encode('utf-8')))
print('[1] 首行:', lines[0][:80])
print('[1] 末行:', lines[-1][:80])
print('[1] 含 author-more 块 =', raw.count('class="author-more"'), ' 次')
print('[1] <?php 开标签 =', raw.count('<?php'), '  ?> 闭标签 =', raw.count('?>'))

# 备份文件
baks = sorted(a.filename for a in sftp.listdir_attr('/D:/workspace/7tan/bbs')
              if a.filename.startswith('view.php.bak_authormore_'))
print('[2] 备份:', baks)

# 清理一次性脚本
junk = ['_explore_tpl.py', '_explore_tpl2.py', '_explore_tpl3.py', '_explore_tpl5.py',
        '_explore_php.py', '_patch_author_more.py', '_dl_profile.py', '_dl_css.py',
        '_srv/_probe2.py', '_srv/_probe_author.py', '_srv/_add_index.py',
        '_srv/view.php.orig', '_srv/view.php.lf']
for j in junk:
    p = ROOT / j
    if p.exists():
        p.unlink()
        print('[3] 删除', j)

print('\n[4] 保留文件:')
for p in sorted(ROOT.glob('_*.py')):
    if p.stat().st_mtime > 1759000000:
        print('   %-28s %6d B' % (p.name, p.stat().st_size))

sftp.close()
ssh.close()
