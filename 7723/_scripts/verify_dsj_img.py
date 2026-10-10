# -*- coding: utf-8 -*-
r"""核验 82484 线上渲染：配图数、原帖按钮数、图片可访问性"""
import io, re, sys, urllib.request, http.cookiejar

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = "https://www.7tan.com"
URL = BASE + "/bbs/82484/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

req = urllib.request.Request(URL, headers=UA)
with urllib.request.urlopen(req, timeout=40) as r:
    page = r.read().decode("utf-8", "ignore")
open(r"D:\7tan\7tanAI\7723\_scripts\_verify_82484_img.html", "w", encoding="utf-8").write(page)

print("标题含 7坛:", "7坛" in page)
print("页内 '点击查看原帖' 次数:", page.count("点击查看原帖"))
# 正文区
body = page.split('class="post-content"', 1)
body = body[1] if len(body) > 1 else page

imgs = re.findall(r'<img[^>]+src="([^"]+)"', body)
imgs = [u for u in imgs if "uploads/image" in u or "7tan.com" in u]
print("正文内图片数:", len(imgs))
for u in imgs:
    print("  ", u)
# 残留 UBB
for tag in ["[img]", "[/img]", "[title]", "[btn=", "[quote]"]:
    print("残留 %-8s : %d" % (tag, body.count(tag)))

# 逐一验证图片可访问
full = []
for u in imgs:
    if u.startswith("//"):
        u = "https:" + u
    elif u.startswith("/"):
        u = BASE + u
    full.append(u)
print("\n图片可访问性:")
for u in full:
    try:
        rq = urllib.request.Request(u, headers=UA, method="GET")
        with urllib.request.urlopen(rq, timeout=40) as r:
            ct = r.headers.get("Content-Type")
            cl = r.headers.get("Content-Length")
            print("  OK %s  %s  %s bytes" % (r.status, ct, cl))
    except Exception as e:
        print("  FAIL", u, repr(e))
