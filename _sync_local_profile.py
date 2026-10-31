# -*- coding: utf-8 -*-
"""把本地 _srv/profile.php 同步成线上分页版，避免下次改到旧副本"""
from pathlib import Path
import hashlib

p = Path(r'D:\7tan\7tanAI\_srv')
new = p / 'profile.new.php'
dst = p / 'profile.php'
b = new.read_bytes()
dst.write_bytes(b)
print('local _srv/profile.php 已同步  %d B  md5=%s' % (len(b), hashlib.md5(b).hexdigest()))
