# -*- coding: utf-8 -*-
import re, io, os, urllib.request

raw = io.open(r"D:\7tan\7tanAI\data\_bjh_raw.html", "r", encoding="utf-8", errors="ignore").read()
imgs = re.findall(r'<img[^>]+src="([^"]+)"', raw)
imgs = [i.replace("&amp;", "&") for i in imgs]
feed = [i for i in imgs if "/feed/" in i]
os.makedirs(r"D:\7tan\7tanAI\data\_bjh_img", exist_ok=True)
log = []
for n, u in enumerate(feed, 1):
    p = r"D:\7tan\7tanAI\data\_bjh_img\%02d.jpg" % n
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://baijiahao.baidu.com/"})
        d = urllib.request.urlopen(req, timeout=30).read()
        io.open(p, "wb").write(d)
        log.append("%02d %d bytes %s" % (n, len(d), u[:100]))
    except Exception as e:
        log.append("%02d FAIL %s %s" % (n, type(e).__name__, str(e)[:80]))
io.open(r"D:\7tan\7tanAI\data\_bjh_img\_log.txt", "w", encoding="utf-8").write("\n".join(log))
