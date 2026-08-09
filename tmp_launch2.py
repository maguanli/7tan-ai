import subprocess, time, sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

exe = r'C:\zd_gfzq_new\TdxW.exe'
cwd = r'C:\zd_gfzq_new'
print('launching...')
p = subprocess.Popen([exe], cwd=cwd)
time.sleep(10)
if p.poll() is None:
    print('RUNNING pid =', p.pid)
else:
    print('EXITED code =', p.returncode)

# 检查相关进程
import os
out = os.popen('tasklist | findstr /i "Tdx GF-Login"').read()
print('tasklist:', out)
