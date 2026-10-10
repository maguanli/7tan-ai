# -*- coding: utf-8 -*-
import urllib.request, re, io
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
req = urllib.request.Request("https://www.7tan.com/bbs/82483/", headers=UA)
h = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')
io.open(r'D:\7tan\7tanAI\7723\_scripts\_verify_82483b.html', 'w', encoding='utf-8').write(h)
print('title_has_7tan:', '7723(7坛) 版主群像' in h)
print('has_num_01:', bool(re.search(r'0\d\s*·\s*存我', h)))
ids = re.findall(r'/bbs/(\d+)/', h)
seen = []
for x in ids:
    if x not in seen:
        seen.append(x)
print('first_ids:', seen[:8])
print('btn_count:', h.count('点击查看原帖'))
