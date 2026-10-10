# -*- coding: utf-8 -*-
import urllib.request, re, io, time
for q in ["?v=1", "?v=999"]:
    req = urllib.request.Request("https://www.7tan.com/bbs/82483/" + q,
                                 headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
    h = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
    m = re.search(r'<meta name="description" content="(.*?)">', h, re.S)
    print(q, '->', (m.group(1)[:160] if m else '(none)'))
    time.sleep(1)
