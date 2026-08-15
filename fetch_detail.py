# -*- coding: utf-8 -*-
import urllib.request, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

url = 'https://www.downkuai.com/android/146875.html'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
html = urllib.request.urlopen(req, timeout=20).read()
# 尝试编码
for enc in ('utf-8', 'gbk', 'gb2312'):
    try:
        text = html.decode(enc)
        break
    except Exception:
        continue
open('detail_146875.html', 'w', encoding='utf-8').write(text)
print('len:', len(text))
# 标题
m = re.search(r'<title>(.*?)</title>', text, re.S)
print('TITLE:', m.group(1).strip() if m else 'N/A')
# 简介段落
for m in re.finditer(r'<p[^>]*>(.*?)</p>', text, re.S):
    t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    t = re.sub(r'\s+', ' ', t)
    if len(t) > 40:
        print('P:', t[:300])
