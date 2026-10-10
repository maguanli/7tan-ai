# -*- coding: utf-8 -*-
r"""更新已发布的《7723(7坛) 大事记》(id 82484) 正文：插入 7 张年份配图"""
import io, re, json, urllib.request, urllib.parse, http.cookiejar, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = "https://www.7tan.com"
PID = "82484"
TITLE = "7723(7坛) 大事记 | 从一个人的WAP手机游戏网，到一群人的七坛（2009—2015·附原帖链接）"
UBB = io.open(r"D:\7tan\7tanAI\7723\7723大事记_配图_UBB.txt", encoding='utf-8').read()
out = []

cj = http.cookiejar.LWPCookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

op.open(urllib.request.Request(BASE + "/bbs/login.php", headers=UA), timeout=30).read()
data = urllib.parse.urlencode({"username": "7723wap", "password": "123466", "redirect": ""}).encode()
with op.open(urllib.request.Request(BASE + "/bbs/login.php", data=data,
        headers={**UA, "Content-Type": "application/x-www-form-urlencoded",
                 "Referer": BASE + "/bbs/login.php"}), timeout=30) as r:
    html = r.read().decode("utf-8", "ignore")
out.append("登录'退出': %s" % ("退出" in html))

# 打开编辑页
with op.open(urllib.request.Request(BASE + "/bbs/edit.php?id=" + PID, headers=UA), timeout=30) as r:
    page = r.read().decode("utf-8", "ignore")
out.append("编辑页: %s | 含原正文(大事记): %s | 标题框: %s" % (
    r.geturl(), ("大事记" in page), ("value=" in page)))
# 找当前标题（用于确认不覆盖错帖）
m = re.search(r'name="title"[^>]*value="([^"]*)"', page)
out.append("现标题: " + (m.group(1) if m else "?"))

d = urllib.parse.urlencode({"title": TITLE, "content": UBB,
                            "fileurl": "", "deleted_files": "[]"}).encode()
with op.open(urllib.request.Request(BASE + "/bbs/edit.php?id=" + PID, data=d,
        headers={**UA, "Content-Type": "application/x-www-form-urlencoded",
                 "Referer": BASE + "/bbs/edit.php?id=" + PID}), timeout=90) as r:
    body = r.read().decode("utf-8", "ignore")
out.append("更新后URL: " + r.geturl())
out.append("含'修改成功': %s | 含'成功': %s" % ("修改成功" in body, "成功" in body))

io.open(r"D:\7tan\7tanAI\7723\_scripts\_edit_dsj.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
