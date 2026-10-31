# -*- coding: utf-8 -*-
import re, urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'ignore')

idx = get('https://www.7tan.com/sitemap.xml')
subs = re.findall(r'<loc>([^<]+)</loc>', idx)
print('sitemap index:', len(subs))
for s in subs:
    print('  ', s)

# 逐个统计 URL 类型
total = 0
kind = {}
for s in subs:
    try:
        x = get(s)
        locs = re.findall(r'<loc>([^<]+)</loc>', x)
        total += len(locs)
        for u in locs:
            path = re.sub(r'^https?://[^/]+', '', u)
            seg = '/' + path.strip('/').split('/')[0]
            kind[seg] = kind.get(seg, 0) + 1
        for pid in ['84008', '83954', '84023', '83897']:
            if any('/bbs/%s/' % pid == re.sub(r'^https?://[^/]+', '', u) for u in locs):
                print('FOUND', pid, 'in', s)
    except Exception as e:
        print('ERR', s, e)
print('total urls', total)
print('by first segment:', sorted(kind.items(), key=lambda x: -x[1])[:12])
