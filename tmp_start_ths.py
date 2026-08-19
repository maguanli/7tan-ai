# -*- coding: utf-8 -*-
import subprocess, time, os

exe = r'C:\同花顺软件\同花顺\hexin.exe'
print("EXISTS:", os.path.exists(exe))
try:
    # DETACHED_PROCESS 避免被父进程结束连带
    CREATE_NO_WINDOW = 0x08000000
    DETACHED = 0x00000008
    p = subprocess.Popen([exe], cwd=os.path.dirname(exe),
                         creationflags=DETACHED | CREATE_NO_WINDOW,
                         close_fds=True)
    print("STARTED PID:", p.pid)
except Exception as e:
    print("ERR:", e)
