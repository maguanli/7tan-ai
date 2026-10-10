# -*- coding: utf-8 -*-
import io
import json
import re

h = open(r"D:\7tan\7tanAI\_sohu_readback.html", encoding="utf-8").read()
t = open(r"D:\7tan\7tanAI\_sohu_readback.txt", encoding="utf-8").read()
blocks = json.load(open(r"D:\7tan\7tanAI\_sohu_blocks.json", encoding="utf-8"))

out = io.StringIO()
w = out.write
w("html=%d txt=%d\n" % (len(h), len(t)))

# 页面里所有 sohu 图片
imgs = re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", h)
sohu = [u for u in imgs if "res.mp.sohu.com" in u]
w("sohu图片=%d\n" % len(sohu))

# 正文文本（去掉脚本样式）
body = re.sub(r"<script.*?</script>", " ", h, flags=re.S)
body = re.sub(r"<style.*?</style>", " ", body, flags=re.S)

# 找编辑器内容区：以第一次出现的 "img-desc" 为锚，向前找容器
w("\n---- 图注编号 ----\n")
w(",".join(re.findall(r"图\s*(\d+)\s*[:：]", t)) + "\n")

w("\n---- 各块是否在页面文本中 ----\n")
page = re.sub(r"\s+", "", t)
for i, b in enumerate(blocks):
    if b["t"] == "text":
        plain = re.sub(r"\s+", "", re.sub(r"<[^<>]+>", "", b["html"]))
        key = plain[:18]
        w("  [%2d] %s  %s\n" % (i, "OK " if key in page else "缺失", key))
    else:
        w("  [%2d] IMG %s\n" % (i, b["path"].split("\\")[-1]))

w("\n---- 星座祈愿段落上下文 ----\n")
idx = page.find("星座祈愿")
w("位置=%d\n" % idx)
if idx >= 0:
    w(page[max(0, idx - 120):idx + 260] + "\n")

w("\n---- 图10 相关 ----\n")
for kw in ["图10", "图11", "天秤", "幸运折扣", "剩余祈愿"]:
    w("  %s -> %d\n" % (kw, page.count(kw)))

open(r"D:\7tan\7tanAI\_sohu_report.txt", "w", encoding="utf-8").write(out.getvalue())
print("written")
