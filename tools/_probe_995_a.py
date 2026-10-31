# -*- coding: utf-8 -*-
"""探测服务器上 7坛 站点结构：找数据库配置 + 定位 995 记录。只读。"""
import json, os, sys
from pathlib import Path
import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(r'D:\7tan\7tanAI')
srv = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))['server']
PHP = r'D:\php\php-8.2.27\php.exe'
SITE = 'D:/workspace/7tan'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
             timeout=25, look_for_keys=False, allow_agent=False)

def run(cmd, timeout=60, limit=4000):
    _i, o, e = ssh.exec_command(cmd, timeout=timeout)
    out = o.read().decode('utf-8', 'ignore')
    err = e.read().decode('utf-8', 'ignore')
    txt = out if out.strip() else err
    return txt[:limit]

print('===== 1. 站点根目录 =====')
print(run('dir /b "%s"' % SITE.replace('/', '\\'), limit=3000))

print('===== 2. 找数据库配置文件 =====')
print(run('dir /s /b "%s\\config*.php" 2>nul' % SITE.replace('/', '\\'), limit=2000))

print('===== 3. php 版本 =====')
print(run('"%s" -v' % PHP, limit=300))
ssh.close()
