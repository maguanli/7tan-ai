# -*- coding: utf-8 -*-
"""检查 SSH 工具链与 deploy.json 可用性（不打印凭据）。"""
import json, os, shutil, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(os.path.join(root, 'config', 'deploy.json'), encoding='utf-8'))
srv = cfg.get('server', {})

print('== deploy.json server 字段 ==')
for k in ('host', 'port', 'user', 'remote_dir', 'remote_manual'):
    v = srv.get(k)
    if k == 'password':
        continue
    print(f'  {k} = {v}')
print('  password: set' if srv.get('password') else '  password: EMPTY')

print('\n== 工具链 ==')
for name in ('ssh', 'scp', 'sftp', 'plink', 'pscp'):
    p = shutil.which(name)
    print(f'  {name}: {p or "NOT FOUND"}')

print('\n== python 库 ==')
for mod in ('paramiko', 'fabric', 'requests'):
    try:
        m = __import__(mod)
        print(f'  {mod}: {getattr(m, "__version__", "ok")}')
    except Exception as e:
        print(f'  {mod}: MISSING ({e.__class__.__name__})')
