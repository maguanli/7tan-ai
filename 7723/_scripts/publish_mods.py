# -*- coding: utf-8 -*-
"""登录 7坛（老马账号 7723wap）并把《7723 版主群像》发到 活动公告(board 16)"""
import io, re, json, urllib.request, urllib.parse, http.cookiejar

BASE = "https://www.7tan.com"
CONF = r"D:\7tan\7tanAI\7723\_scripts\publish_conf.json"
out = []

conf = json.load(open(CONF, encoding='utf-8'))
TITLE = conf['title']
UBB = io.open(conf['content_file'], encoding='utf-8').read()

cj = http.cookiejar.LWPCookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

# 0) 预热
op.open(urllib.request.Request(BASE + "/bbs/login.php", headers=UA), timeout=30).read()

# 1) 登录
data = urllib.parse.urlencode({"username": "7723wap", "password": "123466", "redirect": ""}).encode()
req = urllib.request.Request(BASE + "/bbs/login.php", data=data,
                             headers={**UA, "Content-Type": "application/x-www-form-urlencoded",
                                      "Referer": BASE + "/bbs/login.php"})
with op.open(req, timeout=30) as r:
    html = r.read().decode("utf-8", "ignore")
    out.append("登录后URL: " + r.geturl())
out.append("是否含'退出': %s" % ("退出" in html))

# 2) 发帖
post_data = urllib.parse.urlencode({"bankuai": "16", "title": TITLE,
                                    "content": UBB, "images": ""}).encode()
req2 = urllib.request.Request(BASE + "/bbs/post.php", data=post_data,
                              headers={**UA, "Content-Type": "application/x-www-form-urlencoded",
                                       "Referer": BASE + "/bbs/post.php?bankuai=16"})
try:
    with op.open(req2, timeout=60) as r:
        final = r.geturl()
        body = r.read().decode("utf-8", "ignore")
    out.append("发帖后URL: " + final)
    m = re.search(r"/bbs/(\d+)/", final)
    if m:
        out.append("NEW_POST_ID=" + m.group(1))
    out.append("body[:300]=" + body[:300].replace("\n", " "))
except Exception as e:
    out.append("发帖异常: %r" % e)

io.open(r"D:\7tan\7tanAI\7723\_scripts\_publish_result.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
