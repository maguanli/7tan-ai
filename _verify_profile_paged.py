# -*- coding: utf-8 -*-
"""分页边界实测：单页 / 两页 / 三页 / 空 / 高产作者深页码"""
import io, re, sys, time, urllib.request, urllib.error
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 'https://www.7tan.com'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)


opener = urllib.request.build_opener(NoRedirect)


def get(path):
    req = urllib.request.Request(BASE + path, headers={'User-Agent': UA})
    t0 = time.time()
    try:
        with opener.open(req, timeout=40) as r:
            return r.status, r.read().decode('utf-8', 'ignore'), '', (time.time() - t0) * 1000
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read().decode('utf-8', 'ignore'), ex.headers.get('Location', ''), (time.time() - t0) * 1000


def report(path):
    code, html, loc, ms = get(path)
    if code in (301, 302):
        print('  %-28s %s → %-22s %5.0f ms' % (path, code, loc, ms))
        return
    items = len(re.findall(r'<div class="topic-item">', html))
    badge = re.findall(r'class="count-badge">([^<]*)<', html)
    pager = 'class="pager"' in html
    onpg = re.findall(r'class="pg on">(\d+)<', html)
    pages = re.findall(r'class="pg(?: on)?"[^>]*>(\d+)<', html)
    empty = '这个账号还没有发过帖子' in html
    warn = sum(html.count(k) for k in ('Warning:', 'Notice:', 'Fatal error', 'Deprecated:'))
    can = re.findall(r'<link rel="canonical" href="([^"]+)"', html)
    ttl = re.findall(r'<title>([^<]*)</title>', html)
    print('  %-28s %s  条目=%-2d 徽章=%-24s 分页=%-5s 当前=%-4s 告警=%d %5.0f ms'
          % (path, code, items, ','.join(badge) or '-', pager, ','.join(onpg) or '-', warn, ms))
    print('        canonical=%s' % (can[0] if can else '-'))
    print('        title=%s' % (ttl[0].strip() if ttl else '-'))
    if empty:
        print('        空状态文案 = 是')


print('=== 单页（uid=1689，3 篇）===')
report('/bbs/user/1689/')
report('/bbs/user/1689/?page=2')

print('\n=== 两页（uid=3561，21 篇）===')
report('/bbs/user/3561/')
report('/bbs/user/3561/?page=2')
report('/bbs/user/3561/?page=3')

print('\n=== 三页（uid=2492，41 篇）===')
report('/bbs/user/2492/')
report('/bbs/user/2492/?page=3')

print('\n=== 空账号（uid=20753，0 篇）===')
report('/bbs/user/20753/')

print('\n=== 高产作者（uid=99901，2380 篇 → 119 页）===')
report('/bbs/user/99901/')
report('/bbs/user/99901/?page=60')
report('/bbs/user/99901/?page=119')
report('/bbs/user/99901/?page=120')
