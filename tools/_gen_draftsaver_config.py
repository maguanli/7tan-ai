# -*- coding: utf-8 -*-
"""把 draft_saver 的内置平台档案落地成 config/platforms.json（方便直接改 URL）"""
import importlib.util
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
SRC = Path(r'D:\7tan\7tanAI\data\plugins\draft_saver\tools.py')
spec = importlib.util.spec_from_file_location('draft_saver_tools2', SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

prof = mod._load_profiles()
mod._save_profiles(prof)
p = mod.CONFIG_PATH
print('config 落地:', p)
print('存在:', p.exists(), '| 字节:', p.stat().st_size if p.exists() else 0)
data = json.loads(p.read_text(encoding='utf-8'))
print('平台数:', len(data), '->', sorted(data))
for pid, v in data.items():
    print('  %-10s %-8s %s' % (pid, v.get('name'), v.get('editor_url') or '(空)'))
