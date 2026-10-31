# -*- coding: utf-8 -*-
import re, io, sys, urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'ignore')

def stat(url, label):
    try:
        h = get(url)
    except Exception as e:
        print(label, 'ERR', e)
        return None
    postlinks = sorted(set(re.findall(r'href="(/bbs/\d+/)"', h)))
    boards = sorted(set(re.findall(r'href="(/bbs/board/\d+/)"', h)))
    print('---', label, url)
    print('  bytes', len(h))
    print('  post links', len(postlinks), postlinks[:15])
    print('  board links', len(boards), boards[:15])
    for kw in ['相关阅读', '相关推荐', '延伸阅读', '合集', '专题', '作者其他', '更多文章']:
        if kw in h:
            print('  KW hit:', kw, h.count(kw))
    return h

h1 = stat('https://www.7tan.com/bbs/84008/', 'small village post')
h2 = stat('https://www.7tan.com/bbs/83954/', 'sanguozhi post')

# 作者页 / 搜索页探测
for u in ['https://www.7tan.com/bbs/uid/1/', 'https://www.7tan.com/bbs/user/1/',
          'https://www.7tan.com/bbs/author/1/', 'https://www.7tan.com/bbs/search.php?keyword=test',
          'https://www.7tan.com/bbs/uid1/', 'https://www.7tan.com/bbs/space.php?uid=1']:
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            print('PROBE', u, r.status, len(r.read()))
    except Exception as e:
        print('PROBE', u, 'ERR', e)
