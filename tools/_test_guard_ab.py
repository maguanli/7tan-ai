# -*- coding: utf-8 -*-
"""反向验证：改前的写法（只 print 不 raise）在闸门故障时退出码是 0"""
import io, subprocess, sys, tempfile, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

OLD = '''# -*- coding: utf-8 -*-
import sys
pid, WS, images = 99999, r"D:\\7tan\\dsh-workspace\\article-zcy", [1]*26
try:
    import sys as _gsys
    _gsys.path.insert(0, r'D:\\7tan\\7tanAI\\__not_exist__')
    from publish_guard import guard as _publish_guard
    _publish_guard(pid, WS, expect_images=len(images))
except SystemExit:
    raise
except Exception as _gx:
    print('[9] GUARD self-error (post already published):', repr(_gx))
print("走到末尾 -> 退出码 0")
'''

NEW = OLD.replace(
    '    print(\'[9] GUARD self-error (post already published):\', repr(_gx))\n',
    '    print(\'[9] GUARD self-error (post already published):\', repr(_gx))\n    raise SystemExit(4)\n')

tmpdir = tempfile.mkdtemp()
for tag, code in (('改前', OLD), ('改后', NEW)):
    f = os.path.join(tmpdir, f'{tag}.py')
    open(f, 'w', encoding='utf-8').write(code)
    r = subprocess.run([sys.executable, f], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=120)
    tail = (r.stdout or '').strip().splitlines()
    print(f"  {tag}: 退出码 = {r.returncode}   末行 = {tail[-1][:80] if tail else ''}")

print()
print("  改前 0 = 闸门消失但外层以为成功（Worker 发现的就是这个）")
print("  改后 4 = 失败可见，发布脚本会停住")
