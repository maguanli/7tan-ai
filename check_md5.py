# -*- coding: utf-8 -*-
import hashlib, os
base = r'D:\7tan\7tanAI\dist\release\github'
files = ['7tan-editor-v1.0.13.zip', '7tan-editor-free-v1.0.13.zip', '7tan-web-v1.0.13.zip']
sizes = {}
md5s = {}
for f in files:
    p = os.path.join(base, f)
    if os.path.exists(p):
        sizes[f] = os.path.getsize(p)
        h = hashlib.md5()
        with open(p, 'rb') as fh:
            for chunk in iter(lambda: fh.read(1024*1024), b''):
                h.update(chunk)
        md5s[f] = h.hexdigest()
        print(f"{f}: {sizes[f]/1024/1024:.1f} MB, MD5={md5s[f]}")
    else:
        print(f"{f}: 不存在")
if len(md5s) >= 2:
    e = md5s.get('7tan-editor-v1.0.13.zip')
    fe = md5s.get('7tan-editor-free-v1.0.13.zip')
    if e and fe:
        print("完整版 == 免费版 ?", e == fe)
