# -*- coding: utf-8 -*-
"""对比备份与当前文件：确认 PHP 标签数差异 = 新增块贡献"""
import io, json, sys
from pathlib import Path
import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
cfg = json.loads((Path(r'D:\7tan\7tanAI') / 'config' / 'deploy.json').read_text(encoding='utf-8'))
srv = cfg['server']
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
            timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

base = '/D:/workspace/7tan/bbs/'
bak = sorted(a.filename for a in sftp.listdir_attr(base) if a.filename.startswith('view.php.bak_authormore_'))[-1]


def stat(name):
    f = sftp.open(base + name)
    t = f.read().decode('utf-8', 'ignore')
    f.close()
    return dict(bytes=len(t.encode()), php=t.count('<?php'), close=t.count('?>'),
                short=t.count('<?='), lines=t.count('\r\n') + 1)


a, b = stat(bak), stat('view.php')
print('备份  ', a)
print('当前  ', b)
print('差值  ', {k: b[k] - a[k] for k in a})

sftp.close()
ssh.close()
