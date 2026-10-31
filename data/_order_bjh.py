# -*- coding: utf-8 -*-
import re, io, html as H

raw = io.open(r"D:\7tan\7tanAI\data\_bjh_raw.html", "r", encoding="utf-8", errors="ignore").read()

# tokenize <p>...</p> and <img ...src=feed...> in document order
pat = re.compile(r'(?is)<p[^>]*>(.*?)</p>|<img[^>]+src="([^"]*?/feed/[^"]*)"')
out = []
i = 0
for m in pat.finditer(raw):
    i += 1
    if m.group(1) is not None:
        t = re.sub(r"(?s)<[^>]+>", "", m.group(1))
        t = H.unescape(t).strip()
        if t:
            out.append("P%d %s" % (i, t[:80]))
    else:
        out.append("IMG%d %s" % (i, m.group(2)[:60]))

io.open(r"D:\7tan\7tanAI\data\_bjh_order.txt", "w", encoding="utf-8").write("\n".join(out))
print(len(out))
