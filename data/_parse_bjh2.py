# -*- coding: utf-8 -*-
import sys, re, io

raw = io.open(r"D:\7tan\7tanAI\data\_bjh_raw.html", "r", encoding="utf-8", errors="ignore").read()

# look for known globals
for key in ["__INITIAL_STATE__", "window.__", "articleInfo", "contentData", "sanNodebox", "data-", "rich_media", "ArticleContent", "objData", "landingSuper"]:
    sys.stdout.write("%s -> %d\n" % (key, raw.count(key)))

# find longest chinese runs
runs = re.findall(r"[\u4e00-\u9fa5，。、；：“”‘’？！—…（）《》%0-9A-Za-z\-·]{40,}", raw)
runs.sort(key=len, reverse=True)
sys.stdout.write("RUNS %d\n" % len(runs))
for r in runs[:15]:
    sys.stdout.write("[%d] %s\n" % (len(r), r[:220]))
