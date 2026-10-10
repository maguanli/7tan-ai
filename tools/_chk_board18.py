# -*- coding: utf-8 -*-
"""核验 board/18 与 board/64 的帖子列表，确认《疯狂动物园》评测是否已发布。"""
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36'}
PAGES = ['https://www.7tan.com/bbs/board/18/', 'https://www.7tan.com/bbs/board/18_2/',
         'https://www.7tan.com/bbs/board/18_3/',
         'https://www.7tan.com/bbs/board/64/']

PAT = re.compile(r'<a[^>]+href="/bbs/(\d+)/"[^>]*>(.*?)</a>', re.S)


def clean(s):
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).strip()


for url in PAGES:
    try:
        req = urllib.request.Request(url, headers=UA)
        html = urllib.request.urlopen(req, timeout=25).read().decode('utf-8', 'ignore')
    except Exception as e:
        print(f'== {url} 抓取失败: {e}')
        continue
    seen, rows = set(), []
    for tid, raw in PAT.findall(html):
        t = clean(raw)
        if not t or len(t) < 6 or not re.search(r'[\u4e00-\u9fa5]', t):
            continue
        if tid in seen:
            continue
        seen.add(tid)
        rows.append((tid, t))
    print(f'\n== {url}  页面 {len(html)} 字节  抓到标题 {len(rows)} 条')
    for tid, t in rows[:22]:
        flag = ''
        if '奥特曼' in t:
            flag = '  <<<< 奥特曼'
        if '动物园' in t:
            flag += '  <<<< 疯狂动物园'
        print(f'  {tid}  {t[:52]}{flag}')
    hits = [r for r in rows if '奥特曼' in r[1] or '动物园' in r[1]]
    print(f'  -> 关键词命中 {len(hits)} 条')
