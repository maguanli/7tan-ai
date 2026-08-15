# -*- coding: utf-8 -*-
import pathlib
t = pathlib.Path('tmp_build.log').read_text(encoding='gbk', errors='replace')
lines = t.splitlines()
out = []
# 打印 ERROR / Traceback / Error 附近行
for i, l in enumerate(lines):
    low = l.lower()
    if any(k in low for k in ['error', 'traceback', 'exception', 'failed', 'cannot', 'no module']):
        start = max(0, i - 2)
        end = min(len(lines), i + 6)
        for j in range(start, end):
            out.append(f'{j+1}: {lines[j]}')
        out.append('---')
# 最后 30 行
out.append('=== 最后30行 ===')
out.extend(f'{len(lines)-30+k+1}: {lines[len(lines)-30+k]}' for k in range(min(30, len(lines))))
pathlib.Path('tmp_build_err.txt').write_text('\n'.join(out), encoding='utf-8')
print('OK, total lines:', len(lines))
