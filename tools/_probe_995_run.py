# -*- coding: utf-8 -*-
"""上传探测 PHP 并在服务器执行。只读。"""
import json, sys
from pathlib import Path
import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(r'D:\7tan\7tanAI')
srv = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))['server']
PHP = r'D:\php\php-8.2.27\php.exe'
REMOTE = 'D:/workspace/7tan/updates/_probe_995.php'
LOCAL = ROOT / 'tools' / '_probe_995.php'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
             timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()
sftp.put(str(LOCAL), REMOTE)
print('uploaded ->', REMOTE)

_i, o, e = ssh.exec_command('"%s" "%s"' % (PHP, REMOTE), timeout=120)
out = o.read().decode('utf-8', 'ignore')
err = e.read().decode('utf-8', 'ignore')
print(out[:12000])
if err.strip():
    print('--- STDERR ---')
    print(err[:3000])

sftp.remove(REMOTE)
print('\n(remote probe removed)')
ssh.close()
