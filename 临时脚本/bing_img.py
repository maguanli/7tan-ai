# -*- coding: utf-8 -*-
import requests, re, json, urllib.parse, sys

query = sys.argv[1] if len(sys.argv) > 1 else 'high speed train child window'
url = 'https://www.bing.com/images/search?q=' + urllib.parse.quote(query) + '&qft=+filterui:license-L2_L3_L4'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9'
}
r = requests.get(url, headers=headers, timeout=30)
html = r.text
items = re.findall(r'<a[^>]+class="iusc"[^>]+m="([^"]+)"', html)
print('total items:', len(items))
for i, m in enumerate(items[:20]):
    try:
        data = json.loads(m.replace('&quot;', '"').replace('&amp;', '&'))
        print(i + 1, '|', (data.get('t', '') or '')[:60], '|', data.get('murl', '') or '')
    except Exception as e:
        print(i + 1, 'ERR', e)
