# -*- coding: utf-8 -*-
"""核验 7坛指定帖子：标题 / 作者 / 板块 / 图片数 / 正文长度。"""
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36'}

for tid in sys.argv[1:]:
    url = f'https://www.7tan.com/bbs/{tid}/'
    try:
        html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) \
            .read().decode('utf-8', 'ignore')
    except Exception as e:
        print(f'== {tid} 失败: {e}')
        continue

    def first(pat, default='(未匹配)'):
        m = re.search(pat, html, re.S)
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else default

    title = first(r'<title>(.*?)</title>')
    author = first(r'class="author"[^>]*>(.*?)<')
    board = re.findall(r'list\.php\?id=(\d+)', html)
    date = first(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
    imgs = sorted(set(re.findall(r'https?://img\.7tan\.com/\S+?\.(?:jpg|jpeg|png|gif|webp)', html, re.I)))
    txt = re.sub(r'<script.*?</script>', '', html, flags=re.S)
    txt = re.sub(r'<[^>]+>', '', txt)
    txt = re.sub(r'\s+', '', txt)
    print(f'\n== {url}')
    print(f'   title  : {title[:70]}')
    print(f'   author : {author}')
    print(f'   board  : {sorted(set(board))[:6]}')
    print(f'   time   : {date}')
    print(f'   imgs   : {len(imgs)} 唯一 img.7tan 图')
    print(f'   正文字数: {len(txt)}')
    print(f'   含奥特曼: {"奥特曼" in html}  含疯狂动物园: {"疯狂动物园" in html}')
