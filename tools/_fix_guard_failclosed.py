# -*- coding: utf-8 -*-
"""修复：闸门自身故障被静默吞掉（fail-open -> fail-closed）

问题（Worker 验收时发现，我已复核）：
    12 个 publish_*.py 末尾的闸门块是
        try:
            from publish_guard import guard as _publish_guard
            _publish_guard(pid, WS, expect_images=len(images))
        except SystemExit:
            raise
        except Exception as _gx:
            print('[9] GUARD self-error (post already published):', repr(_gx))

    若 publish_guard 导入失败 / bbs_verify.py 缺失或被改写，只打印一行，
    然后正常退出（退出码 0）—— 闸门消失而外层无感知。

修法：
    except Exception 分支改为 raise SystemExit(4)：
        - 帖子已发布但没验成，属于「结果未知」，必须让外层停下
        - 退出码 4 与 bbs_verify 的 0/1 和三方超时 3 区分开

做法：
    1. 先把 12 个文件复制到 _backup_guard_<时间戳>/（可回滚）
    2. 精确替换那一行 print，追加 raise SystemExit(4)
    3. 语法检查 + 逐个确认改动行
"""
import io, os, re, shutil, sys, time, py_compile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

WS = r'D:\7tan\dsh-workspace'
STAMP = time.strftime('%Y%m%d_%H%M%S')
BACKUP = os.path.join(WS, f'_backup_guard_{STAMP}')

TARGETS = [
    r'article-boke-doudizhu\publish_bkddz.py',
    r'article-dqdh\publish_dqdh.py',
    r'article-jiangshi-zhazhiji\publish_jszzj.py',
    r'article-qiqiu-yingxiong\publish_qqyx.py',
    r'article-shaonian-sanguozhi\publish_snsgz.py',
    r'article-xdkz3d\publish_xdkz3d.py',
    r'article-xiaoxiao-cunzhang\publish_xxcz.py',
    r'article-zaomengxiyou4\publish_zmxy4.py',
    r'article-zcy\publish_zcy.py',
    r'phone-clean-24gb\publish_phoneclean.py',
    r'salt-hidden\publish_salt.py',
    r'sugar-35\publish_sugar35.py',
]

# 要匹配的那一行（容错空格）
PAT = re.compile(
    r'^(?P<indent>[ \t]*)print\((?P<q>[\'\"])\[9\] GUARD self-error \(post already published\):(?P=q),\s*repr\(_gx\)\)\s*$',
    re.M)

print("=" * 64)
print("备份到:", BACKUP)
os.makedirs(BACKUP, exist_ok=True)

ok, fail = [], []
for rel in TARGETS:
    p = os.path.join(WS, rel)
    dst = os.path.join(BACKUP, rel.replace('\\', '__'))
    if not os.path.exists(p):
        fail.append((rel, '文件不存在'))
        continue
    shutil.copy2(p, dst)
    ok.append(rel)
print(f"备份成功 {len(ok)} 个，失败 {len(fail)} 个")
for r, why in fail:
    print("   ❌", r, why)

print()
print("=" * 64)
print("检查当前状态")
print("=" * 64)
state = {}
for rel in ok:
    p = os.path.join(WS, rel)
    src = open(p, encoding='utf-8').read()
    m = PAT.search(src)
    has_raise4 = 'raise SystemExit(4)' in src
    state[rel] = {'match': m, 'raise4': has_raise4, 'path': p, 'src': src}
    tag = '已修' if has_raise4 else ('待修' if m else '模式不匹配')
    print(f"  {rel:45s} {tag}")

print()
print("=" * 64)
print("执行替换")
print("=" * 64)
changed, skipped = [], []
for rel, st in state.items():
    if st['raise4']:
        skipped.append(rel)
        continue
    if not st['match']:
        fail.append((rel, '锚点行未匹配，未改'))
        continue
    m = st['match']
    indent = m.group('indent')
    q = m.group('q')
    new_line = (f'{indent}print({q}[9] GUARD self-error (post already published):{q}, '
                f'repr(_gx))\n'
                f'{indent}raise SystemExit(4)   # 闸门自身故障 = 失败，不能静默放行')
    new_src = st['src'][:m.start()] + new_line + st['src'][m.end():]
    open(st['path'], 'w', encoding='utf-8', newline='').write(new_src)
    changed.append(rel)

print(f"已修改 {len(changed)} 个，跳过（本来就有）{len(skipped)} 个")
for r in changed:
    print("   ✏️ ", r)

print()
print("=" * 64)
print("语法检查 + 复核")
print("=" * 64)
allbad = 0
for rel in TARGETS:
    p = os.path.join(WS, rel)
    if not os.path.exists(p):
        continue
    try:
        py_compile.compile(p, doraise=True, quiet=1)
        syn = 'OK'
    except Exception as e:
        syn = f'SYNTAX FAIL: {e}'
        allbad += 1
    src = open(p, encoding='utf-8').read()
    n4 = src.count('raise SystemExit(4)')
    nprint = len(PAT.findall(src))
    print(f"  {rel:45s} 语法={syn:6s} SystemExit(4)={n4}  残留裸print={nprint}")
    if n4 != 1:
        allbad += 1

print()
print("结论:", "✅ 全部通过" if allbad == 0 else f"❌ {allbad} 处异常")
print("回滚:", f"把 {BACKUP} 里的文件复制回原位置即可")
