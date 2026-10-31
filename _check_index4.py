# -*- coding: utf-8 -*-
import re, urllib.request, urllib.parse

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'ignore'), r.status

h, st = get('https://www.7tan.com/bbs/search.php')
# 找出 ajax 端点
for pat in [r'fetch\(([^)]{0,120})\)', r'\.open\([^)]{0,120}\)', r'xmlhttp[^;]{0,120}', r'url\s*:\s*[\'"][^\'"]+[\'"]', r'action=[\'"][^\'"]+[\'"]']:
    hits = re.findall(pat, h, flags=re.I)
    if hits:
        print('PAT', pat[:30], '->', hits[:6])

# 尝试可能的 ajax 搜索端点
for u in ['https://www.7tan.com/bbs/search_api.php?keyword=' + urllib.parse.quote('小小村长'),
          'https://www.7tan.com/bbs/api/search.php?keyword=' + urllib.parse.quote('小小村长'),
          'https://www.7tan.com/bbs/search.php?keyword=' + urllib.parse.quote('小小村长') + '&ajax=1']:
    try:
        hh, ss = get(u)
        n = len(re.findall(r'/bbs/\d{5}/', hh))
        print('AJAX', u.split('?')[0], ss, len(hh), 'postlinks', n)
        print('   sample:', re.sub(r'\s+',' ', re.sub(r'<[^>]+>',' ', hh))[:200])
    except Exception as e:
        print('AJAX', u, 'ERR', e)
