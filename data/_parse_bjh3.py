# -*- coding: utf-8 -*-
import re, io, html as H

raw = io.open(r"D:\7tan\7tanAI\data\_bjh_raw.html", "r", encoding="utf-8", errors="ignore").read()

# 1) locate landed content region: baijiahao embeds content inside <div id="ssr-content"> or similar
# try to find all paragraphs
body = raw

# remove scripts/styles
body2 = re.sub(r"(?is)<script.*?</script>", " ", body)
body2 = re.sub(r"(?is)<style.*?</style>", " ", body2)

# get text nodes
text = re.sub(r"(?s)<[^>]+>", "\n", body2)
text = H.unescape(text)
lines = [l.strip() for l in text.split("\n")]
lines = [l for l in lines if l]

out = io.open(r"D:\7tan\7tanAI\data\_bjh_text.txt", "w", encoding="utf-8")
out.write("\n".join(lines))
out.close()

# also dump raw paragraphs tags
ps = re.findall(r"(?is)<p[^>]*>(.*?)</p>", raw)
res = []
for p in ps:
    t = re.sub(r"(?s)<[^>]+>", "", p)
    t = H.unescape(t).strip()
    if t:
        res.append(t)
out2 = io.open(r"D:\7tan\7tanAI\data\_bjh_ps.txt", "w", encoding="utf-8")
out2.write("\n\n".join(res))
out2.close()

with io.open(r"D:\7tan\7tanAI\data\_bjh_meta.txt", "w", encoding="utf-8") as f:
    f.write("raw_len %d\n" % len(raw))
    f.write("lines %d\n" % len(lines))
    f.write("ps %d\n" % len(ps))
    f.write("ps_nonempty %d\n" % len(res))
    f.write("ps_chars %d\n" % sum(len(x) for x in res))
    imgs = re.findall(r'<img[^>]+src="([^"]+)"', raw)
    f.write("imgs %d\n" % len(imgs))
    for i in imgs[:40]:
        f.write("  IMG %s\n" % i[:160])
