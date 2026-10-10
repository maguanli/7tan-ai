# -*- coding: utf-8 -*-
"""登录 7坛，抓发帖页/编辑页，查找图片上传接口与 [img] 语法"""
import io, re, urllib.request, urllib.parse, http.cookiejar, sys

BASE = "https://www.7tan.com"
cj = http.cookiejar.LWPCookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
out = []

op.open(urllib.request.Request(BASE + "/bbs/login.php", headers=UA), timeout=30).read()
data = urllib.parse.urlencode({"username": "7723wap", "password": "123466", "redirect": ""}).encode()
req = urllib.request.Request(BASE + "/bbs/login.php", data=data,
                             headers={**UA, "Content-Type": "application/x-www-form-urlencoded",
                                      "Referer": BASE + "/bbs/login.php"})
with op.open(req, timeout=30) as r:
    html = r.read().decode("utf-8", "ignore")
    out.append("登录后URL: " + r.geturl())
out.append("含'退出': %s" % ("退出" in html))

for path in ["/bbs/post.php", "/bbs/post.php?bankuai=16", "/bbs/post/"]:
    try:
        with op.open(urllib.request.Request(BASE + path, headers=UA), timeout=30) as r:
            body = r.read().decode("utf-8", "ignore")
            out.append("\n=== GET %s -> %s (len=%d) ===" % (path, r.geturl(), len(body)))
            # 找 form action / 上传相关
            for m in re.finditer(r'<form[^>]*>', body):
                out.append("FORM: " + m.group(0)[:200])
            for kw in ["upload", "image", "图片", "file", "accept=", "enctype"]:
                hits = [x.group(0)[:160] for x in re.finditer(r'.{60}' + kw + r'.{60}', body)]
                if hits:
                    out.append("[%s] %d hits:" % (kw, len(hits)))
                    for h in hits[:6]:
                        out.append("   " + h.replace("\n", " "))
            # 找 JS 里的 fetch/ajax 上传
            for m in re.finditer(r'(fetch|XMLHttpRequest|\.post|action)\s*[\(=]\s*["\']([^"\']{3,80})', body):
                out.append("JS_post: " + m.group(2))
    except Exception as e:
        out.append("GET %s 异常 %r" % (path, e))

io.open(r"D:\7tan\7tanAI\7723\_scripts\_probe_upload.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
