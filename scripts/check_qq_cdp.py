# -*- coding: utf-8 -*-
"""检查QQ进程命令行参数（找CDP调试端口）和监听端口"""
import psutil
import subprocess
import sys
import re

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 1. QQ 进程命令行
print('=== QQ 进程命令行 ===')
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        name = (p.info['name'] or '').lower()
        if 'qq' in name and p.info['cmdline']:
            cmd = ' '.join(p.info['cmdline'])
            if len(cmd) > 30:
                print(f'PID={p.info["pid"]}: {cmd[:300]}')
    except Exception:
        pass

# 2. 监听端口（找 922x/9xxx 调试端口）
print('\n=== 常见调试端口检查 ===')
import socket
for port in [9222, 9223, 9229, 9333, 17890, 9222+1]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(('127.0.0.1', port))
        print(f'  端口 {port}: 开放')
    except Exception:
        pass
    finally:
        s.close()
