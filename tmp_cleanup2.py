# -*- coding: utf-8 -*-
"""清理临时文件 + 计算新包 MD5"""
import os, sys, hashlib, shutil
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 1) 删除临时脚本
tmp_files = [
    'tmp_diag_pack.py', 'tmp_diag_pack2.py', 'tmp_check_zip_plugins.py',
    'tmp_check_web_zip.py', 'tmp_check_src_plugins.py', 'tmp_cmp_plugins.py',
    'tmp_check_dist.py', 'tmp_reproduce.py', 'tmp_verify_syntax.py',
    'tmp_verify_newpkg.py', 'tmp_verify_static.py', 'tmp_verify_dynamic.py',
    'tmp_clean_webtest.py',
]
for f in tmp_files:
    fp = os.path.join(r'D:\7tan\7tanAI', f)
    if os.path.exists(fp):
        try:
            os.remove(fp)
            print(f"[del] {f}")
        except Exception as e:
            print(f"[fail] {f}: {e}")

# 2) 删除临时解压目录
for d in ['tmp_webtest', 'tmp_webtest2', 'tmp_webtest3']:
    dp = os.path.join(r'D:\7tan\7tanAI', d)
    if os.path.exists(dp):
        try:
            shutil.rmtree(dp, ignore_errors=True)
            print(f"[del-dir] {d}" + ("" if not os.path.exists(dp) else " (仍存在)"))
        except Exception:
            print(f"[fail-dir] {d}")

# 3) 计算新包 MD5
print()
print("新包 MD5：")
for name in ['7tan-editor-v1.0.15.zip', '7tan-web-v1.0.15.zip']:
    fp = os.path.join(r'D:\7tan\7tanAI\dist\release', name)
    if os.path.exists(fp):
        h = hashlib.md5()
        size = 0
        with open(fp, 'rb') as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
                size += len(chunk)
        print(f"  {name}: md5={h.hexdigest()} size={size}")
    else:
        print(f"  {name}: 不存在")
print("DONE-CLEANUP")
