# -*- coding: utf-8 -*-
"""临时：删除 git index.lock"""
from pathlib import Path
p = Path(".git/index.lock")
if p.exists():
    p.unlink()
    print("LOCK_REMOVED")
else:
    print("NO_LOCK")
