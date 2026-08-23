# -*- coding: utf-8 -*-
import os
base = r'D:\7tan\7tanAI'
for name in os.listdir(base):
    if '镜像' in name or 'С˵' in name or name.endswith('_С˵') or name.endswith('_小说') or 'ͬ' in name:
        print('FOUND:', repr(name), name.encode('utf-8'))
