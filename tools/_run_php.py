# -*- coding: utf-8 -*-
"""通用：上传本地 php 到服务器执行，然后删除。argv[1]=本地php文件 argv[2]=超时"""
import json, sys
from pathlib import Path
import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(r'D:\7tan\7tanAI')
srv = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))['server']
PHP = r'D:\php\php-8.2.27\php.exe'

local = Path(sys.argv[1])
timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 120
name = local.name
remote = 'D:/workspace/7tan/updates/_tmp_' + name

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
             timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()
sftp.put(str(local), remote)

_i, o, e = ssh.exec_command('"%s" "%s"' % (PHP, remote), timeout=timeout)
out = o.read().decode('utf-8', 'ignore')
err = e.read().decode('utf-8', 'ignore')
print(out[:20000])
if err.strip():
    print('--- STDERR ---')
    print(err[:4000])

try:
    sftp.remove(remote)
except Exception:
    pass
ssh.close()
