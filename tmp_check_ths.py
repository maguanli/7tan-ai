# -*- coding: utf-8 -*-
import os

d = r'C:\同花顺软件\同花顺'
try:
    files = sorted(os.listdir(d))
    print("TOTAL:", len(files))
    for f in files:
        if f.lower().endswith(('.exe', '.bat', '.lnk')):
            print("EXE/CMD:", f)
        elif 'hexin' in f.lower() or 'xiadan' in f.lower() or 'ths' in f.lower():
            print("KEY:", f)
except Exception as e:
    print("ERR:", e)
