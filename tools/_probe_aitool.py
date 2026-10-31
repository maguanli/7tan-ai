# -*- coding: utf-8 -*-
"""查 ai-tool 目录结构与版本号出现位置（只读）"""
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

def run(cmd, timeout=60, limit=5000):
    _i, o, e = ssh.exec_command(cmd, timeout=timeout)
    out = o.read().decode('utf-8', 'ignore')
    err = e.read().decode('utf-8', 'ignore')
    return (out if out.strip() else err)[:limit]

print('===== ai-tool 目录 =====')
print(run(r'dir /b "D:\workspace\7tan\ai-tool"'))

print('===== ai-tool 下含 1.0.2x 的文件 =====')
print(run(r'findstr /s /i /m "1.0.22" "D:\workspace\7tan\ai-tool\*.*"', limit=3000))

print('===== 命中行 =====')
print(run(r'findstr /s /i /n "1.0.22 1.0.23" "D:\workspace\7tan\ai-tool\*.php" "D:\workspace\7tan\ai-tool\*.html"', limit=6000))

print('===== index.php 大小 =====')
print(run(r'dir "D:\workspace\7tan\ai-tool\index.php"'))
ssh.close()
