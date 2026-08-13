# -*- coding: utf-8 -*-
"""临时：清理所有 _tmp / 调试临时文件"""
from pathlib import Path

files = [
    "_pkg_log.txt", "_tmp_check2.py", "_tmp_check_imports.py",
    "_tmp_del_old_pkgs.py", "_tmp_run_pkg.py", "_tmp_size.py",
    "_tmp_size2.py", "_tmp_size_stats.py", "_tmp_verify_pkg.py",
]
for f in files:
    p = Path(f)
    if p.exists():
        p.unlink()
        print("DEL", f)
    else:
        print("SKIP", f)
print("CLEANED")
