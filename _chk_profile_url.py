# -*- coding: utf-8 -*-
import re, urllib.request, json

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode('utf-8', 'replace'), dict(r.headers)

res = {}

# 1. 帖子页里的 profile / user 链接
st, html, hd = get('https://www.7tan.com/bbs/84008/')
res['post_status'] = st
res['post_len'] = len(html)

prof = re.findall(r'href="([^"]*profile\.php[^"]*)"', html)
usr = re.findall(r'href="([^"]*user/\d+[^"]*)"', html)
res['profile_links_in_post'] = sorted(set(prof))
res['user_links_in_post'] = sorted(set(usr))

# 2. author-more 模块原文
i = html.find('author-more')
res['author_more_found'] = i > 0
if i > 0:
    res['author_more_html'] = html[i-300:i+2500]

# 3. 干净的 user URL 是否可用
for u in ['https://www.7tan.com/bbs/user/99908/',
          'https://www.7tan.com/bbs/user/99908/?page=2']:
    try:
        s, h, hh = get(u)
        res[u] = {'status': s, 'len': len(h), 'canonical': (re.search(r'<link rel="canonical" href="([^"]*)"', h).group(1) if re.search(r'<link rel="canonical" href="([^"]*)"', h) else None),
                  'title': (re.search(r'<title>(.*?)</title>', h, re.S).group(1).strip() if re.search(r'<title>(.*?)</title>', h, re.S) else None),
                  'has_noindex': 'noindex' in h.lower()}
    except Exception as e:
        res[u] = {'error': str(e)}

# 4. profile.php 动态版的状态码与 canonical
for u in ['https://www.7tan.com/bbs/profile.php?id=99908',
          'https://www.7tan.com/bbs/profile.php?id=99908&page=2']:
    try:
        s, h, hh = get(u)
        res[u] = {'status': s, 'len': len(h),
                  'canonical': (re.search(r'<link rel="canonical" href="([^"]*)"', h).group(1) if re.search(r'<link rel="canonical" href="([^"]*)"', h) else None),
                  'title': (re.search(r'<title>(.*?)</title>', h, re.S).group(1).strip() if re.search(r'<title>(.*?)</title>', h, re.S) else None),
                  'robots': (re.search(r'<meta name="robots" content="([^"]*)"', h).group(1) if re.search(r'<meta name="robots" content="([^"]*)"', h) else None)}
    except Exception as e:
        res[u] = {'error': str(e)}

print(json.dumps(res, ensure_ascii=False, indent=2))
