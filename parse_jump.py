# -*- coding: utf-8 -*-
import urllib.request, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

url = 'https://get.downkuai.com/jump.php?target=SzI3VBVGVCl7F2J7FyBLIy9USAQGBTMLXipCB04jbUcJDkJaGFVWN1MHQD9uSA8EDxxwTVAzSQ==&type=1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'ignore')
open('jump_page.html', 'w', encoding='utf-8').write(html)
print('saved, len=', len(html))

for m in re.findall(r'["\'](https?://[^"\']+)["\']', html):
    print('URL:', m)
for m in re.findall(r'location\s*[.=][^;]{0,150}', html):
    print('JS:', m)
for m in re.findall(r'href="([^"]+)"', html):
    print('HREF:', m)
