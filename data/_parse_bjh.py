# -*- coding: utf-8 -*-
import sys, re, io, html as H

raw = io.open(r"D:\7tan\7tanAI\data\_bjh_raw.html", "r", encoding="utf-8", errors="ignore").read()

def show(label, v):
    sys.stdout.write("%s: %s\n" % (label, v))

# meta
for pat, name in [
    (r'"author"\s*:\s*"([^"]{0,60})"', "author"),
    (r'"source"\s*:\s*"([^"]{0,60})"', "source"),
    (r'"publishTime"\s*:\s*"?([^",]{0,40})', "publishTime"),
    (r'"pub_time"\s*:\s*"?([^",]{0,40})', "pub_time"),
    (r'itemprop=dateUpdate content="([^"]+)"', "dateUpdate"),
    (r'"author_name"\s*:\s*"([^"]{0,60})"', "author_name"),
]:
    mm = re.findall(pat, raw)
    if mm:
        show(name, mm[:3])

for key in ["article-content", "articleContent", "main-content", "san-nodebox", "bjh-article", "article_source"]:
    show("count_" + key, raw.count(key))
