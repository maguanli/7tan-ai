# -*- coding: utf-8 -*-
"""验证修改后文件语法"""
import py_compile, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

files = [
    r'D:\7tan\7tanAI\src\database\db.py',
    r'D:\7tan\7tanAI\templates\package_release.py',
]
ok = True
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"[OK] {f}")
    except Exception as e:
        ok = False
        print(f"[FAIL] {f}: {e}")

# build.spec 语法（不执行 import，只编译）
spec = r'D:\7tan\7tanAI\build.spec'
try:
    src = open(spec, encoding='utf-8').read()
    compile(src, 'build.spec', 'exec')
    print(f"[OK] {spec} (语法编译通过)")
except Exception as e:
    ok = False
    print(f"[FAIL] {spec}: {e}")

print("ALL_OK" if ok else "HAS_FAIL")
