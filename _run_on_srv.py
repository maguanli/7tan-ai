# -*- coding: utf-8 -*-
"""把脚本传到服务器 D:\\temp 下执行，回传 stdout"""
import io, json, sys
from pathlib import Path
import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

local = Path(sys.argv[1])
ROOT = Path(r'D:\7tan\7tanAI')
cfg = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))
srv = cfg['server']

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
            timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

remote = '/D:/temp/' + local.name
with sftp.open(remote, 'wb') as f:
    f.write(local.read_bytes())
print('[up]', remote, local.stat().st_size, 'B')

cmd = 'python D:\\temp\\%s 2>&1' % local.name
_, out, err = ssh.exec_command(cmd, timeout=180)
o = out.read().decode('utf-8', 'ignore')
e = err.read().decode('utf-8', 'ignore')
print('[out]')
print(o)
if e.strip():
    print('[err]', e[:1500])

sftp.remove(remote)
print('[clean] 已删除远端临时脚本')
sftp.close()
ssh.close()
