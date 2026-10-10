# -*- coding: utf-8 -*-
import re
h = open(r"D:\7tan\7tanAI\_sohu_readback.html", encoding="utf-8").read()
# 去掉 header 部分
h = h.split("<!--StartFragment-->", 1)[-1]
parts = re.split(r"(<img[^>]*>)", h)
i = 0
for p in parts:
    if p.startswith("<img"):
        src = re.search(r'src=["\']([^"\']+)', p)
        print("  >>>IMG  %s" % (src.group(1)[:60] if src else "?"))
        continue
    txt = re.sub(r"<[^<>]+>", " ", p)
    txt = re.sub(r"\s+", " ", txt).strip()
    txt = txt.replace("此图片描述少于60个字， 编辑", "")
    txt = txt.strip()
    if not txt:
        continue
    print("  TXT  %s" % txt[:70])
print("=== 含 '图10' 次数:", h.count("图10"), " 图11:", h.count("图11"))
