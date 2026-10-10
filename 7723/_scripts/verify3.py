# -*- coding: utf-8 -*-
import urllib.request, re, io
req = urllib.request.Request("https://www.7tan.com/bbs/82483/", headers={"User-Agent": "Mozilla/5.0"})
h = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
io.open(r"D:\7tan\7tanAI\7723\_scripts\_verify_82483.html", "w", encoding="utf-8").write(h)
res = []
m = re.search(r'<meta name="description" content="(.*?)">', h, re.S)
res.append("DESC: " + (m.group(1)[:220] if m else '(none)'))
res.append("ubb-button: %d | ubb-title: %d | ubb-quote: %d | ubb-sep: %d" %
           (h.count('class="ubb-button"'), h.count('class="ubb-title"'), h.count('class="ubb-quote"'), h.count('class="ubb-sep"')))
res.append("原帖链接数: %d" % len(re.findall(r'href="https://www\.7tan\.com/bbs/\d+/"', h)))
i = h.find('class="post-content"')
res.append("BODY开头: " + re.sub(r'\s+', ' ', h[i:i + 700]))
io.open(r"D:\7tan\7tanAI\7723\_scripts\_verify3.txt", "w", encoding="utf-8").write("\n".join(res))
print("ok")
