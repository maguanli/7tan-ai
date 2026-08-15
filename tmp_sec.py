# -*- coding: utf-8 -*-
import pathlib

out = []
# scripts/tmp/file_version_info.txt 是否存在
p = pathlib.Path('scripts/tmp/file_version_info.txt')
out.append(f'{"OK " if p.exists() else "MISS"} scripts/tmp/file_version_info.txt ({p.stat().st_size}B)' if p.exists() else f'MISS scripts/tmp/file_version_info.txt')

# src/security 目录内容
out.append('\n=== src/security/ ===')
sec = pathlib.Path('src/security')
if sec.exists():
    for f in sorted(sec.iterdir()):
        out.append(f'  {f.name}')

# src/agent 目录（web_console_tts 也在 hiddenimports）
out.append('\n=== src/agent/ ===')
ag = pathlib.Path('src/agent')
if ag.exists():
    for f in sorted(ag.iterdir()):
        out.append(f'  {f.name}')

pathlib.Path('tmp_sec.txt').write_text('\n'.join(out), encoding='utf-8')
print('OK')
