# -*- coding: utf-8 -*-
"""把 publish_guard 调用注入到各 publish_*.py 末尾（幂等，可重复运行）

在末尾 print('PID =', pid, ...) 之后追加闸门代码。
已注入的跳过；缺 WS/images 变量的跳过。
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BLOCK = '''

# ---------- 9. 独立断言闸门（Watchdog：失败即非0退出） ----------
try:
    import sys as _gsys
    _gsys.path.insert(0, r'D:\\7tan\\7tanAI\\tools')
    from publish_guard import guard as _publish_guard
    _publish_guard(pid, WS, expect_images=len(images))
except SystemExit:
    raise
except Exception as _gx:
    print('[9] GUARD self-error (post already published):', repr(_gx))
'''

ANCHOR = "print('PID =', pid, ' URL =', URL)"

targets = sorted(Path(r'D:\7tan\dsh-workspace').glob('*/publish_*.py'))
print('found publish scripts: %d' % len(targets))

for p in targets:
    txt = p.read_text(encoding='utf-8', errors='replace')
    name = p.parent.name + '/' + p.name
    if '_publish_guard' in txt:
        print('  SKIP already   %s' % name)
        continue
    if ANCHOR not in txt:
        print('  MISS no anchor %s' % name)
        continue
    lack = [k for k in ('WS', 'images') if k not in txt]
    if lack:
        print('  MISS no vars   %s -> %s' % (name, lack))
        continue
    idx = txt.rindex(ANCHOR) + len(ANCHOR)
    new = txt[:idx] + BLOCK + txt[idx:]
    p.write_text(new, encoding='utf-8')
    print('  OK   injected  %s  (+%d bytes)' % (name, len(BLOCK.encode('utf-8'))))
