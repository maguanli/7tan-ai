# -*- coding: utf-8 -*-
"""注入后自检：语法 + guard 正反两向测试"""
import glob
import py_compile
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

print('=== 1. 语法检查 12 个 publish 脚本 ===')
fs = sorted(glob.glob(r'D:\7tan\dsh-workspace\*\publish_*.py'))
bad = []
for f in fs:
    try:
        py_compile.compile(f, doraise=True)
    except Exception as e:
        bad.append((f, str(e)[:120]))
print('  编译 %d 个，失败 %d 个' % (len(fs), len(bad)))
for f, e in bad:
    print('  FAIL', f, e)

print('\n=== 2. 检查注入块存在且位置在末尾 ===')
ok = 0
for f in fs:
    t = open(f, encoding='utf-8', errors='replace').read()
    if '_publish_guard(pid, WS, expect_images=len(images))' in t:
        ok += 1
print('  已注入 %d / %d' % (ok, len(fs)))

print('\n=== 3. guard 正向测试：84149 + 正确文章目录（应 PASS/rc=0）===')
r1 = subprocess.run(
    [sys.executable, r'D:\7tan\7tanAI\tools\publish_guard.py', '84149',
     '--article-dir', r'D:\7tan\dsh-workspace\article-zcy'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
print('  rc =', r1.returncode)
print('  tail:', (r1.stdout or '').strip().splitlines()[-3:])

print('\n=== 4. guard 反向测试：84149 + 错误文章目录（应 FAIL/rc!=0）===')
r2 = subprocess.run(
    [sys.executable, r'D:\7tan\7tanAI\tools\publish_guard.py', '84149',
     '--article-dir', r'D:\7tan\dsh-workspace\article-xdkz3d'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
print('  rc =', r2.returncode)
print('  tail:', (r2.stdout or '').strip().splitlines()[-4:])

print('\n=== 5. guard 反向测试：不存在的 pid（应 rc!=0）===')
r3 = subprocess.run(
    [sys.executable, r'D:\7tan\7tanAI\tools\publish_guard.py', '99999999'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
print('  rc =', r3.returncode)

print('\n=== 结论 ===')
print('  语法     :', 'PASS' if not bad else 'FAIL')
print('  注入     :', 'PASS' if ok == len(fs) else 'FAIL')
print('  正向闸门 :', 'PASS' if r1.returncode == 0 else 'FAIL rc=%d' % r1.returncode)
print('  反向闸门 :', 'PASS' if r2.returncode != 0 else 'FAIL 错了也判通过')
print('  无效pid  :', 'PASS' if r3.returncode != 0 else 'FAIL 错了也判通过')
