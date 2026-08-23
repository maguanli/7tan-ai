# -*- coding: utf-8 -*-
import os, sys
print('PYTHONIOENCODING:', sys.stdout.encoding)
base = r'D:\7tan\7tanAI'
for name in os.listdir(base):
    print(repr(name))
