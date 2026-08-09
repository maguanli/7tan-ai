import os, subprocess, sys

# 启动广发金融终端（通过桌面快捷方式，保证工作目录正确）
lnk = r'C:\Users\Administrator\Desktop\金融终端.lnk'
exe = r'C:\zd_gfzq_new\TdxW.exe'

try:
    if os.path.exists(lnk):
        os.startfile(lnk)
        print('STARTED via lnk:', lnk)
    else:
        os.startfile(exe)
        print('STARTED via exe:', exe)
except Exception as e:
    print('ERR', e)
    sys.exit(1)
