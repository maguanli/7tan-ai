# -*- coding: utf-8 -*-
import pathlib

out = []
# 1. 磁盘上是否存在相关文件
for name in ['file_version_info.txt', 'src/web/api_chat.py', 'src/web/routes/api_chat.py',
             'src/security/trial_store.py']:
    p = pathlib.Path(name)
    out.append(f'{"OK " if p.exists() else "MISS"} {name}')

# 2. build.spec 中 version 与 hiddenimports 相关行
out.append('\n=== build.spec version/hiddenimports ===')
spec = pathlib.Path('build.spec').read_text(encoding='utf-8', errors='replace')
for i, l in enumerate(spec.splitlines(), 1):
    if 'version' in l.lower() or 'hiddenimport' in l.lower() or 'api_chat' in l or 'trial_store' in l or 'icon' in l.lower():
        out.append(f'{i}: {l.strip()[:160]}')

# 3. git 历史中 file_version_info.txt 是否存在
out.append('\n=== git ls-files file_version_info ===')
import subprocess
r = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, encoding='utf-8', errors='replace')
for f in r.stdout.splitlines():
    if 'version_info' in f or 'file_version' in f:
        out.append(f)

pathlib.Path('tmp_fix_build.txt').write_text('\n'.join(out), encoding='utf-8')
print('OK')
