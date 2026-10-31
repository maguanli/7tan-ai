# -*- coding: utf-8 -*-
"""读服务器上的 config.php / db.php，本地脱敏后打印结构。"""
import json, re, sys
from pathlib import Path
import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(r'D:\7tan\7tanAI')
srv = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))['server']

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
             timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

SENSITIVE = re.compile(r'(pass|pwd|secret|key|token)', re.I)

def dump(remote, maxlen=3000):
    print('=' * 20, remote)
    try:
        with sftp.open(remote, 'r') as f:
            raw = f.read()
    except Exception as e:
        print('  READ FAIL:', e)
        return
    if isinstance(raw, bytes):
        txt = raw.decode('utf-8', 'ignore')
    else:
        txt = raw
    out = []
    for line in txt.splitlines():
        # 对含敏感词的行，只保留赋值号左侧
        if SENSITIVE.search(line) and '=' in line:
            left = line.split('=')[0]
            out.append(left.rstrip() + ' = <hidden>')
        else:
            out.append(line)
    body = '\n'.join(out)
    print(body[:maxlen])
    print()

dump('D:/workspace/7tan/config.php')
dump('D:/workspace/7tan/db.php', 2000)
dump('D:/workspace/7tan/db_creds.php', 1200)
ssh.close()
