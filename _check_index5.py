# -*- coding: utf-8 -*-
import re, json, urllib.request, urllib.parse

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def api(kw):
    u = 'https://www.7tan.com/bbs/search_api.php?keyword=' + urllib.parse.quote(kw)
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode('utf-8', 'ignore'))
    res = d.get('results', [])
    return d.get('code'), len(res), [(x.get('id'), x.get('ll_idd'), (x.get('ll_biaoti') or '')[:30]) for x in res]

for kw in ['小小村长', '少年三国志', '测评', '阵位']:
    try:
        code, n, items = api(kw)
        print('KW', kw, 'code', code, 'n', n)
        for it in items[:8]:
            print('   ', it)
    except Exception as e:
        print('KW', kw, 'ERR', e)

# 作者页到底列几篇
req = urllib.request.Request('https://www.7tan.com/bbs/user/1/', headers=UA)
h = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')
ids = re.findall(r'href="(/bbs/\d+/)"', h)
print('\nuser/1 post links:', ids)
m = re.search(r'(主题|发帖|文章)[^0-9]{0,6}([\d,]+)', re.sub(r'<[^>]+>', ' ', h))
print('user/1 stat:', m.groups() if m else None)
