# -*- coding: utf-8 -*-
import sys, re, io, json
import urllib.request

url = "https://baijiahao.baidu.com/s?id=1880574095793533424&wfr=spider&for=pc"
req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.baidu.com/",
})
raw = urllib.request.urlopen(req, timeout=40).read()
html = raw.decode("utf-8", "ignore")
out = io.open(r"D:\7tan\7tanAI\data\_bjh_raw.html", "w", encoding="utf-8")
out.write(html)
out.close()
sys.stdout.write("LEN %d\n" % len(html))
m = re.search(r"<title>(.*?)</title>", html, re.S)
sys.stdout.write("TITLE %s\n" % (m.group(1) if m else "NONE"))
