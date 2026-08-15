# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def fetch(keyword):
    url = 'https://search.downkuai.com/?keyword=' + urllib.parse.quote(keyword)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'ignore')
    return html

html = fetch('月圆之夜')
items = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S)
for href, inner in items:
    text = re.sub(r'<[^>]+>', '', inner).strip()
    text = re.sub(r'\s+', ' ', text)
    if text and 'downkuai.com' in href and ('android' in href or 'soft' in href or 'zt' in href):
        print(f'{text}  =>  {href}')
