# -*- coding: utf-8 -*-
import urllib.request, re, io

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "ignore")

h = get("https://www.7tan.com/bbs/82483/")
io.open(r"D:\7tan\7tanAI\7723\_scripts\_verify_82483.html", "w", encoding="utf-8").write(h)
res = []
res.append("page bytes: %d" % len(h))
res.append("ubb-button (按钮/原帖链接): %d" % h.count('class="ubb-button"'))
res.append("ubb-title  : %d" % h.count('class="ubb-title"'))
res.append("ubb-caption: %d" % h.count('class="ubb-caption"'))
res.append("ubb-quote  : %d" % h.count('class="ubb-quote"'))
res.append("ubb-note   : %d" % h.count('class="ubb-note"'))
res.append("ubb-sep    : %d" % h.count('class="ubb-sep"'))
res.append("原始未解析 [title] 残留: %d" % h.count('[title]'))
res.append("原始未解析 [btn= 残留: %d" % h.count('[btn='))
res.append("指向老帖的链接 /bbs/5470/ 等: %d" % len(re.findall(r'href="https://www\.7tan\.com/bbs/\d+/"', h)))
# 抓正文区片段
m = re.search(r'(?is)<div[^>]*class="[^"]*(?:post-content|topic-content|ubb-content)[^"]*"[^>]*>(.*?)</div>', h)
if m:
    seg = re.sub(r'\s+', ' ', m.group(1))[:600]
    res.append("BODY: " + seg)
else:
    # 退而求其次：找第一个 ubb-title 附近
    i = h.find('ubb-title')
    res.append("near: " + re.sub(r'\s+', ' ', h[max(0, i - 200):i + 600]))
io.open(r"D:\7tan\7tanAI\7723\_scripts\_verify.txt", "w", encoding="utf-8").write("\n".join(res))
print("\n".join(res))
