# -*- coding: utf-8 -*-
"""更新已发布的《7723 版主群像》(id 82483) 正文"""
import io, re, json, urllib.request, urllib.parse, http.cookiejar

BASE = "https://www.7tan.com"
PID = "82483"
conf = json.load(open(r"D:\7tan\7tanAI\7723\_scripts\publish_conf.json", encoding='utf-8'))
TITLE = conf['title']
UBB = io.open(conf['content_file'], encoding='utf-8').read()
out = []

cj = http.cookiejar.LWPCookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

op.open(urllib.request.Request(BASE + "/bbs/login.php", headers=UA), timeout=30).read()
data = urllib.parse.urlencode({"username": "7723wap", "password": "123466", "redirect": ""}).encode()
req = urllib.request.Request(BASE + "/bbs/login.php", data=data,
                             headers={**UA, "Content-Type": "application/x-www-form-urlencoded",
                                      "Referer": BASE + "/bbs/login.php"})
with op.open(req, timeout=30) as r:
    html = r.read().decode("utf-8", "ignore")
out.append("登录'退出': %s" % ("退出" in html))

# 打开编辑页确认权限
try:
    with op.open(urllib.request.Request(BASE + "/bbs/edit.php?id=" + PID, headers=UA), timeout=30) as r:
        page = r.read().decode("utf-8", "ignore")
    out.append("编辑页可访问: %s | 含原正文: %s" % (r.geturl(), ("版主群像" in page)))
except Exception as e:
    out.append("编辑页异常: %r" % e)

d = urllib.parse.urlencode({"title": TITLE, "content": UBB,
                            "fileurl": "", "deleted_files": "[]"}).encode()
req2 = urllib.request.Request(BASE + "/bbs/edit.php?id=" + PID, data=d,
                              headers={**UA, "Content-Type": "application/x-www-form-urlencoded",
                                       "Referer": BASE + "/bbs/edit.php?id=" + PID})
with op.open(req2, timeout=60) as r:
    body = r.read().decode("utf-8", "ignore")
out.append("更新返回URL: " + r.geturl())
out.append("是否含'修改成功': %s" % ("修改成功" in body))
io.open(r"D:\7tan\7tanAI\7723\_scripts\_edit_result.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
