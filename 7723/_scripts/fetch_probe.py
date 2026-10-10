# -*- coding: utf-8 -*-
import urllib.request, re, sys

def get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'ignore')

html = get('https://www.7tan.com/bbs/65362/')
open(r'D:\7tan\7tanAI\7723\_scripts\_probe_65362.html', 'w', encoding='utf-8').write(html)

# 定位正文区
m = re.search(r'(?is)<div[^>]*class="[^"]*(?:post-content|ubb-content|thread-content|view-content|detail|post-body)[^"]*"[^>]*>(.*?)</div>\s*</div>', html)
print('body regex:', bool(m))
# 找所有 <a href 出现，看是否含 bbs/ 或 5252
links = re.findall(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.I|re.S)
print('links total:', len(links))
for h, t in links:
    if '5252' in h or '5252' in t or '/bbs/' in h and 'login' not in h:
        print('LINK:', h, '||', re.sub(r'<[^>]+>', '', t)[:60])

# 看正文区是否包含原始 (url= 文本（说明未解析）
print('has raw url-ubb:', '(url=' in html)

# 打印包含 5252.cn 的段落上下文
i = html.find('5252网址导航')
print('---- context around 5252 ----')
print(html[i-600:i+400] if i > 0 else 'not found')
