# -*- coding: utf-8 -*-
"""以分离进程启动重启 VBS，并等待 5 秒回读日志确认其独立存活。"""
import io
import sys
import time
import subprocess
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

VBS = r'D:\7tan\7tanAI\tmp\restart_stagefix.vbs'
LOG = Path(r'D:\7tan\7tanAI\tmp\restart_stagefix_log.txt')

if LOG.exists():
    LOG.unlink()

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000

p = subprocess.Popen(
    ['wscript.exe', VBS],
    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
    close_fds=True,
)
print('已启动 wscript.exe  pid =', p.pid)

time.sleep(5)
print('--- 5 秒后回读日志 ---')
if LOG.exists():
    print(LOG.read_text(encoding='utf-8', errors='replace').strip())
else:
    print('(日志未生成 —— 分离启动可能未成功)')
