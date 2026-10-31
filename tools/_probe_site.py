# -*- coding: utf-8 -*-
import os, glob, json

base = r'D:\workspace\7tan'
print('exists:', os.path.isdir(base))
if os.path.isdir(base):
    for p in sorted(glob.glob(os.path.join(base, '*')))[:50]:
        tag = '<DIR>' if os.path.isdir(p) else ''
        print(' ', os.path.basename(p), tag)
