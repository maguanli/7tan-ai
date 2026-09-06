# -*- coding: utf-8 -*-
import subprocess
r = subprocess.run(['wmic', 'process', 'where', 'processid=6168', 'get', 'CommandLine', '/value'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20)
print((r.stdout or '').strip()[:2000])
