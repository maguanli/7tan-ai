# -*- coding: utf-8 -*-
import re, urllib.request, json

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'ignore')

# 1) /bbs/user/1/ 有什么
h = get('https://www.7tan.com/bbs/user/1/')
print('user/1 bytes', len(h))
print('post links:', sorted(set(re.findall(r'href="(/bbs/\d+/)"', h)))[:30])
txt = re.sub(r'<[^>]+>', ' ', h)
txt = re.sub(r'\s+', ' ', txt)
print('text sample:', txt[:400])

# 2) board/18 首页：谁在发帖
h2 = get('https://www.7tan.com/bbs/board/18/')
titles = re.findall(r'href="(/bbs/\d+/)"[^>]*>([^<]{4,80})', h2)
print('\nboard18 page1 post links:', len(set(x[0] for x in titles)))
for pid, t in sorted(set(titles))[:25]:
    print('  ', pid, t.strip()[:50])

# 3) 搜索页能否搜到他的文章
for kw in ['小小村长', '少年三国志', '测评']:
    try:
        hs = get('https://www.7tan.com/bbs/search.php?keyword=' + urllib.parse.quote(kw))
        ids = sorted(set(re.findall(r'href="(/bbs/\d+/)"', hs)))
        print('\nsearch', kw, 'bytes', len(hs), 'hits', len(ids), ids[:10])
    except Exception as e:
        print('search', kw, 'ERR', e)
