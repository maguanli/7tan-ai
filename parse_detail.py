# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

text = open('detail_146875.html', encoding='utf-8').read()

print('=== 图片 ===')
imgs = re.findall(r'<img[^>]*src="([^"]+)"', text)
seen = set()
for u in imgs:
    if u not in seen:
        seen.add(u)
        print(u)

print()
print('=== 下载链接候选 ===')
for m in re.finditer(r'href="([^"]+)"', text):
    u = m.group(1)
    if re.search(r'\.(apk|zip|rar|exe|7z)(\?|$)', u, re.I) or 'down' in u.lower() or 'apk' in u.lower():
        print(u)

print()
print('=== 版本/大小/更新 ===')
for pat in [r'版本[：:]\s*([^<\s]+)', r'大小[：:]\s*([^<\s]+)', r'更新[：:日期]\s*([^<\s]+)', r'语言[：:]\s*([^<\s]+)', r'系统[：:]\s*([^<\s]+)', r'厂商[：:]\s*([^<\s]+)', r'分类[：:]\s*([^<\s]+)']:
    m = re.search(pat, text)
    if m:
        print(pat[:10], '=>', m.group(1).strip()[:50])
