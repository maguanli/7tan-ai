# -*- coding: utf-8 -*-
"""备份将改动的两个源文件，并记录字节/MD5/行尾，便于改后逐项核对。"""
import io
import sys
import hashlib
import shutil
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(r'D:\7tan\7tanAI')
FILES = [
    ROOT / 'src/agent/upper_m2_autobiography.py',
    ROOT / 'src/web/routes/api_mind.py',
]

for f in FILES:
    if not f.exists():
        print('[MISS] 不存在:', f)
        continue
    b = f.read_bytes()
    crlf = b.count(b'\r\n')
    lf = b.count(b'\n')
    print('%-34s %7d B  md5=%s  CRLF=%d  LF=%d' % (f.name, len(b), hashlib.md5(b).hexdigest(), crlf, lf))
    bak = f.with_name(f.name + '.bak_stage_fix')
    shutil.copy2(f, bak)
    bb = bak.read_bytes()
    print('   备份 -> %-42s %7d B  SAME=%s' % (bak.name, len(bb), bb == b))
print('备份完成')
