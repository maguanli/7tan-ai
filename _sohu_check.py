# -*- coding: utf-8 -*-
import re
h = open(r"D:\7tan\7tanAI\_sohu_readback.html", encoding="utf-8").read()
t = open(r"D:\7tan\7tanAI\_sohu_readback.txt", encoding="utf-8").read()
print("html=%d txt=%d" % (len(h), len(t)))
print("图片数 img=", len(re.findall(r"<img", h)))
print("图注数 图N: =", len(re.findall(r"图\s*\d+\s*[:：]", t)))
caps = re.findall(r"图\s*(\d+)\s*[:：]", t)
print("图注编号:", ",".join(caps))
print("h2=", len(re.findall(r"<h2", h)), " h1=", len(re.findall(r"<h1", h)))
print("blockquote=", len(re.findall(r"<blockquote", h)))
print("strong=", len(re.findall(r"<strong", h)))
# 每个 img 后面紧跟的文字片段
for m in re.finditer(r"<img[^>]*>", h):
    after = re.sub(r"<[^<>]+>", " ", h[m.end():m.end() + 220])
    after = re.sub(r"\s+", " ", after).strip()
    print("   IMG -> %s" % after[:60])
print("---- 文本开头 ----")
print(re.sub(r"\s+", " ", t)[:300])
print("---- 文本结尾 ----")
print(re.sub(r"\s+", " ", t)[-300:])
for k in ["迷你世界", "回帖", "评论区", "综合", "综上"]:
    print("关键字 %s = %d" % (k, t.count(k)))
