# -*- coding: utf-8 -*-
import re, socket

html = open(r"D:\7tan\7tanAI\_anfensi_home.html", "rb").read().decode("utf-8", "ignore")
# 文件是用 utf-8 写的，但原始内容可能是 gbk 误解码，重新从原始字节取
raw = open(r"D:\7tan\7tanAI\_anfensi_home.html", "rb").read()

for enc in ("gbk", "gb18030", "utf-8"):
    try:
        t = raw.decode(enc, "ignore")
        m = re.search(r"<title>(.*?)</title>", t, re.S | re.I)
        title = m.group(1).strip() if m else ""
        ok = sum(1 for c in title if "\u4e00" <= c <= "\u9fff")
        print("[%s] 汉字数=%d title=%s" % (enc, ok, title[:80]))
    except Exception as e:
        print(enc, "ERR", e)

t = raw.decode("gb18030", "ignore")
m = re.search(r"<title>(.*?)</title>", t, re.S | re.I)
print()
print("最终 title:", (m.group(1).strip() if m else "无")[:100])
print("字数:", len(t))
for kw in ["安粉丝", "关停", "关闭", "维护", "迁移", "公告", "停机", "暂停"]:
    print("关键词", kw, t.count(kw))
m2 = re.search(r'name="description"\s+content="(.*?)"', t, re.S | re.I)
print("description:", (m2.group(1)[:150] if m2 else "无"))

# 最新更新时间线索
for pat in [r"20\d\d-\d\d-\d\d", r"\d{2}-\d{2} \d{2}:\d{2}"]:
    found = re.findall(pat, t)
    if found:
        from collections import Counter
        c = Counter(found).most_common(5)
        print("时间样式", pat, "->", c)
