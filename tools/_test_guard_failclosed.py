# -*- coding: utf-8 -*-
"""行为验证：闸门自身故障时是否 fail-closed（退出码 4）

方法：复刻 12 个脚本里那段一模一样的 try/except 结构，
      分别注入三种故障，看子进程退出码。
"""
import io, subprocess, sys, tempfile, os, textwrap
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TEMPLATE = '''# -*- coding: utf-8 -*-
import sys
{MOCK}
pid, WS, images = 99999, r"D:\\7tan\\dsh-workspace\\article-zcy", [1]*26

# ---------- 9. 独立断言闸门（与原脚本结构一致） ----------
try:
    import sys as _gsys
    _gsys.path.insert(0, r'{PATH_INSERT}')
    from publish_guard import guard as _publish_guard
    _publish_guard(pid, WS, expect_images=len(images))
except SystemExit:
    raise
except Exception as _gx:
    print('[9] GUARD self-error (post already published):', repr(_gx))
    raise SystemExit(4)   # 闸门自身故障 = 失败，不能静默放行
print("正常走到末尾，退出码 0")
'''

CASES = {
    'A. 正常（publish_guard 可导入，但 pid 不存在->bbs_verify 判 FAIL）': r'D:\7tan\7tanAI\tools',
    'B. 故障（路径里没有 publish_guard，导入失败）': r'D:\7tan\7tanAI\__not_exist__',
}

tmpdir = tempfile.mkdtemp()
for name, pathxx in CASES.items():
    code = TEMPLATE.format(MOCK='', PATH_INSERT=pathxx)
    f = os.path.join(tmpdir, 'case.py')
    open(f, 'w', encoding='utf-8').write(code)
    r = subprocess.run([sys.executable, f], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=300)
    rc = r.returncode
    out = (r.stdout or '').strip().splitlines()
    err = (r.stderr or '').strip().splitlines()
    print("=" * 66)
    print(name)
    print("  退出码:", rc)
    if out:
        print("  stdout 末行:", out[-1][:120])
    if err:
        print("  stderr 末行:", err[-1][:120])

print()
print("=" * 66)
print("判定")
print("=" * 66)
print("  A 应为 1（bbs_verify 有 FAIL）—— 真实断言生效")
print("  B 应为 4（闸门自身故障）—— 这是本次修复的目标，改前会是 0")
