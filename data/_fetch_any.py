# -*- coding: utf-8 -*-
import sys, re, io, html as H
import urllib.request

url = sys.argv[1]
outp = sys.argv[2]
req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
})
raw = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")

# strip scripts/styles
body = re.sub(r"(?is)<script.*?</script>", " ", raw)
body = re.sub(r"(?is)<style.*?</style>", " ", body)
# article body: take paragraphs
ps = re.findall(r"(?is)<p[^>]*>(.*?)</p>", body)
lines = []
for p in ps:
    t = re.sub(r"(?s)<[^>]+>", "", p)
    t = H.unescape(t).replace("\u00a0", " ").strip()
    if t and len(t) > 1:
        lines.append(t)
io.open(outp, "w", encoding="utf-8").write("\n\n".join(lines))
sys.stdout.write("PS %d CHARS %d\n" % (len(lines), sum(len(x) for x in lines)))
