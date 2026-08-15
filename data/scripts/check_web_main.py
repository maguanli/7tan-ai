# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\7tan\7tanAI\web_main.py', encoding='utf-8') as f:
    content = f.read()
# 打印前 3000 字符 + 所有包含 host/port/127.0.0.1/0.0.0.0 的行
print('===== 前 3000 字符 =====')
print(content[:3000])
print('===== host/port 相关行 =====')
for i, line in enumerate(content.splitlines(), 1):
    low = line.lower()
    if 'host' in low or 'port' in low or '127.0.0.1' in low or '0.0.0.0' in low:
        print(i, line.strip()[:160])
