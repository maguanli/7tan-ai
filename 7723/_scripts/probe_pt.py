# -*- coding: utf-8 -*-
"""抓取发帖页 window.PT 完整配置，定位图片上传接口"""
import io, re, urllib.request, urllib.parse, http.cookiejar

BASE = "https://www.7tan.com"
cj = http.cookiejar.LWPCookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

op.open(urllib.request.Request(BASE + "/bbs/login.php", headers=UA), timeout=30).read()
data = urllib.parse.urlencode({"username": "7723wap", "password": "123466", "redirect": ""}).encode()
op.open(urllib.request.Request(BASE + "/bbs/login.php", data=data,
        headers={**UA, "Content-Type": "application/x-www-form-urlencoded",
                 "Referer": BASE + "/bbs/login.php"}), timeout=30).read()

with op.open(urllib.request.Request(BASE + "/bbs/post.php?bankuai=16", headers=UA), timeout=30) as r:
    body = r.read().decode("utf-8", "ignore")
io.open(r"D:\7tan\7tanAI\7723\_scripts\_probe_post_page.html", "w", encoding="utf-8").write(body)

out = []
m = re.search(r'window\.PT\s*=\s*(\{.*?\})\s*;', body, re.S)
if m:
    out.append("PT_CONFIG:\n" + m.group(1))
out.append("\n-- upload/url 线索 --")
for kw in ["upload", r"\.php", "action=", r"img\.7tan", "FormData", "XMLHttpRequest"]:
    for x in re.finditer(r'.{80}' + kw + r'.{80}', body):
        out.append("[%s] %s" % (kw, x.group(0).replace("\n", " ")))
out.append("\n-- scripts --")
for x in re.finditer(r'<script[^>]*src="([^"]+)"', body):
    out.append(x.group(1))
out.append("\n-- form fields --")
for x in re.finditer(r'<(input|textarea|select)[^>]*name="([^"]+)"[^>]*>', body):
    out.append(x.group(0)[:200])
out.append("\n-- enctype/accept --")
for x in re.finditer(r'(enctype="[^"]*"|accept="[^"]*"|type="file")', body):
    out.append(x.group(0))

io.open(r"D:\7tan\7tanAI\7723\_scripts\_probe_pt.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out)[:8000])
