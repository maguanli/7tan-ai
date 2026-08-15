# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, re, sys

def fetch(keyword):
    url = 'https://search.downkuai.com/?keyword=' + urllib.parse.quote(keyword)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'ignore')
    return html

html = fetch('中秋')
open('search_zhongqiu.html', 'w', encoding='utf-8').write(html)
print('HTML len:', len(html))

# 提取所有结果条目：通常是 <div class="..."><a href="...">标题</a>...
# 先找所有 a 标签及其 href 和文本
items = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S)
for href, inner in items:
    text = re.sub(r'<[^>]+>', '', inner).strip()
    text = re.sub(r'\s+', ' ', text)
    if text and 'downkuai.com' in href and not href.endswith('.css') and not href.endswith('.png') and not href.endswith('.jpg'):
        print(f'{text}  =>  {href}')
