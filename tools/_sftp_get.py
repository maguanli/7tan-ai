# -*- coding: utf-8 -*-
"""SFTP 下载服务器文件到本地。argv[1]=远程路径 argv[2]=本地路径"""
import json, sys
from pathlib import Path
import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(r'D:\7tan\7tanAI')
srv = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))['server']

remote, local = sys.argv[1], sys.argv[2]
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
             timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()
sftp.get(remote, local)
st = sftp.stat(remote)
print('DOWNLOADED', remote, '->', local, 'size=%d' % st.st_size)
ssh.close()
