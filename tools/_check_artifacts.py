# -*- coding: utf-8 -*-
"""核对发布产物：version.json 是否指向 1.0.23、md5/size 是否与磁盘文件一致"""
import hashlib, json, os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(r'D:\7tan\7tanAI')
vj = json.loads((ROOT / 'website' / 'updates' / 'version.json').read_text(encoding='utf-8'))
v0 = vj['versions'][0]
print('version.json 首条:')
for k, v in v0.items():
    if k == 'changelog':
        print(f'  {k}: <{len(v)} chars>')
    else:
        print(f'  {k}: {v}')

print('\n磁盘文件核对:')
for name in ('7tan-editor-free-v1.0.23.zip', '7tan-web-v1.0.23.zip'):
    p = ROOT / 'dist' / 'release' / name
    if not p.exists():
        print(f'  {name}: MISSING')
        continue
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(4 << 20), b''):
            h.update(chunk)
    md5 = h.hexdigest()
    size = p.stat().st_size
    sig = p.with_suffix(p.suffix + '.sig')
    print(f'  {name}')
    print(f'    size = {size:,} B')
    print(f'    md5  = {md5}')
    print(f'    sig  = {"OK" if sig.exists() else "MISSING"} ({sig.stat().st_size if sig.exists() else 0} B)')
    # 与 version.json 比对
    if name.startswith('7tan-editor'):
        m = (v0.get('md5') == md5)
        s = (int(v0.get('size', 0)) == size)
        print(f'    version.json md5  匹配: {m}')
        print(f'    version.json size 匹配: {s}')

print('\nupdates 目录里的 sig 是否与 dist 一致:')
for name in ('7tan-editor-free-v1.0.23.zip.sig', '7tan-web-v1.0.23.zip.sig'):
    a = ROOT / 'dist' / 'release' / name
    b = ROOT / 'website' / 'updates' / name
    if a.exists() and b.exists():
        ha = hashlib.md5(a.read_bytes()).hexdigest()[:12]
        hb = hashlib.md5(b.read_bytes()).hexdigest()[:12]
        print(f'  {name}: dist={ha} web={hb} {"SAME" if ha == hb else "DIFF!"}')
    else:
        print(f'  {name}: missing somewhere (dist={a.exists()} web={b.exists()})')
