# -*- coding: utf-8 -*-
"""探查 4：用 SFTP 列目录，避开 PowerShell 转义"""
import io, json, sys, stat
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


def ls(p, show_all=True):
    try:
        items = sftp.listdir_attr(p)
    except Exception as ex:
        print('  !! %s -> %r' % (p, ex))
        return []
    rows = []
    for a in items:
        isdir = stat.S_ISDIR(a.st_mode)
        rows.append((isdir, a.st_size, a.filename))
    rows.sort(key=lambda r: (not r[0], r[2].lower()))
    for isdir, size, name in rows:
        print('  %s %10d  %s' % ('DIR ' if isdir else 'file', 0 if isdir else size, name))
    return rows


print('=== /D:/workspace/7tan/bbs ===')
ls('/D:/workspace/7tan/bbs')

print('\n=== /D:/nginx/nginx-1.24.0/conf ===')
ls('/D:/nginx/nginx-1.24.0/conf')

sftp.close()
ssh.close()
