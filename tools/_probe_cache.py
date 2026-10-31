# -*- coding: utf-8 -*-
"""查站点缓存目录结构与 995 相关缓存（只读）"""
import json, sys
from pathlib import Path
import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(r'D:\7tan\7tanAI')
srv = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))['server']

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
             timeout=25, look_for_keys=False, allow_agent=False)

def run(cmd, timeout=60, limit=4000):
    _i, o, e = ssh.exec_command(cmd, timeout=timeout)
    out = o.read().decode('utf-8', 'ignore')
    err = e.read().decode('utf-8', 'ignore')
    return (out if out.strip() else err)[:limit]

S = r'D:\workspace\7tan'
print('===== cache 顶层 =====')
print(run(r'dir /b "%s\cache"' % S, limit=2000))

print('===== cache 下与 995 / game 相关 =====')
print(run(r'dir /s /b "%s\cache\*995*" 2>nul' % S, limit=2000))
print(run(r'dir /b "%s\cache\game" 2>nul' % S, limit=2000))

print('===== game 目录 =====')
print(run(r'dir /b "%s\game" 2>nul' % S, limit=1500))

print('===== 995 目录 =====')
print(run(r'dir /s /b "%s\game\995\*" 2>nul' % S, limit=2000))
ssh.close()
