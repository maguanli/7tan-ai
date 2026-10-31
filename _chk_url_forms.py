# -*- coding: utf-8 -*-
import re, urllib.request, urllib.error, json

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:
        return -1, str(e)

res = {}

# A. 站内其他地方用的用户链接格式
pages = {
    'board18': 'https://www.7tan.com/bbs/board/18/',
    'post84008': 'https://www.7tan.com/bbs/84008/',
    'home': 'https://www.7tan.com/',
    'profile99908': 'https://www.7tan.com/bbs/profile.php?id=99908',
    'user99908': 'https://www.7tan.com/bbs/user/99908/',
}
for k, u in pages.items():
    st, h = get(u)
    d = {'status': st, 'len': len(h)}
    d['profile_php'] = sorted(set(re.findall(r'href="([^"]*profile\.php[^"?]*(?:\?[^"]*)?)"', h)))
    d['user_clean'] = sorted(set(re.findall(r'href="([^"]*user/\d+[^"]*)"', h)))
    res[k] = d

# B. 各种美化分页 URL 试一遍
cands = [
    'https://www.7tan.com/bbs/user/99908/2/',
    'https://www.7tan.com/bbs/user/99908_2/',
    'https://www.7tan.com/bbs/user/99908/page/2/',
    'https://www.7tan.com/bbs/user/99908/p2/',
    'https://www.7tan.com/bbs/user/99908?page=2',
]
res['pretty_tests'] = {}
for u in cands:
    st, h = get(u)
    t = re.search(r'<title>(.*?)</title>', h, re.S)
    res['pretty_tests'][u] = {'status': st, 'len': len(h), 'title': (t.group(1).strip() if t else None)}

# C. sitemap 里有没有 user 页
res['sitemap_user'] = {}
for f in ['sitemap_zh_1.xml','sitemap_pages.xml']:
    st, h = get('https://www.7tan.com/' + f)
    res['sitemap_user'][f] = {'status': st, 'len': len(h), 'user_urls': len(re.findall(r'/bbs/user/', h))}

# D. robots.txt
st, h = get('https://www.7tan.com/robots.txt')
res['robots'] = h

print(json.dumps(res, ensure_ascii=False, indent=2))
