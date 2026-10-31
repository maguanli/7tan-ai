# -*- coding: utf-8 -*-
"""下载 view.php / load_replies.php 到本地检查"""
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

OUT = Path(r'D:\7tan\7tanAI\_srv')
OUT.mkdir(exist_ok=True)
for f in ['view.php', 'load_replies.php', 'config.php', 'user.php', 'privacy.php']:
    remote = '/D:/workspace/7tan/bbs/' + f
    local = OUT / f
    sftp.get(remote, str(local))
    print('%-20s %8d bytes' % (f, local.stat().st_size))

sftp.close()
ssh.close()
