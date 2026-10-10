# -*- coding: utf-8 -*-
r"""测试 7坛图片上传接口 /bbs/upload_image.php（字段名 image）"""
import io, json, os, sys, uuid, urllib.request, urllib.parse, http.cookiejar, mimetypes

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = "https://www.7tan.com"
cj = http.cookiejar.LWPCookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

op.open(urllib.request.Request(BASE + "/bbs/login.php", headers=UA), timeout=30).read()
data = urllib.parse.urlencode({"username": "7723wap", "password": "123466", "redirect": ""}).encode()
r = op.open(urllib.request.Request(BASE + "/bbs/login.php", data=data,
        headers={**UA, "Content-Type": "application/x-www-form-urlencoded",
                 "Referer": BASE + "/bbs/login.php"}), timeout=30)
print("登录后URL:", r.geturl())

img = r"D:\7tan\7tanAI\7723\img\y2012.png"   # 先用小的试
fn = os.path.basename(img)
with open(img, "rb") as f:
    content = f.read()
boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
body = b""
body += ("--%s\r\n" % boundary).encode()
body += ('Content-Disposition: form-data; name="image"; filename="%s"\r\n' % fn).encode()
body += b"Content-Type: image/png\r\n\r\n"
body += content + b"\r\n"
body += ("--%s--\r\n" % boundary).encode()

req = urllib.request.Request(BASE + "/bbs/upload_image.php", data=body,
        headers={**UA, "Content-Type": "multipart/form-data; boundary=" + boundary,
                 "Referer": BASE + "/bbs/post.php?bankuai=16",
                 "X-Requested-With": "XMLHttpRequest"})
try:
    with op.open(req, timeout=120) as resp:
        txt = resp.read().decode("utf-8", "ignore")
        print("HTTP", resp.status)
        print("响应:", txt[:1000])
except Exception as e:
    print("异常:", repr(e))
