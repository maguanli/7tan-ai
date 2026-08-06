# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mss
with mss.mss() as sct:
    for i, m in enumerate(sct.monitors):
        print(i, m)
