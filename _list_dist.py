# -*- coding: utf-8 -*-
import os
d = r"D:\7tan\7tanAI\dist"
for x in os.listdir(d):
    full = os.path.join(d, x)
    print(repr(x), "DIR" if os.path.isdir(full) else "FILE", os.path.getsize(full) if os.path.isfile(full) else "")
