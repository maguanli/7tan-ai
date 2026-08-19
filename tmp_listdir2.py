# -*- coding: utf-8 -*-
import os

root = 'C:/'
for d in sorted(os.listdir(root)):
    p = os.path.join(root, d)
    if os.path.isdir(p) and not d.isascii():
        print("DIR:", repr(d))
        try:
            for f in sorted(os.listdir(p))[:50]:
                print("   ", repr(f))
        except Exception as e:
            print("   ERR:", e)
