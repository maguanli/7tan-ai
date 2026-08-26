# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
d = r'D:\7tan\7tanAI\data'
for f in sorted(os.listdir(d)):
    p = os.path.join(d, f)
    if os.path.isfile(p):
        print(f"{f}  ({os.path.getsize(p)/1024:.1f} KB)")
    else:
        print(f"{f}/  (目录)")
