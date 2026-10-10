# -*- coding: utf-8 -*-
r"""把 7 张年份图上传到 7坛 /bbs/upload_image.php，记录外链到 img_urls.json"""
import io, json, os, sys, uuid, urllib.request, urllib.parse, http.cookiejar, time

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
print("登录:", r.geturl())


def upload(path):
    fn = os.path.basename(path)
    content = open(path, "rb").read()
    b = "----WebKitFormBoundary" + uuid.uuid4().hex
    body = b""
    body += ("--%s\r\n" % b).encode()
    body += ('Content-Disposition: form-data; name="image"; filename="%s"\r\n' % fn).encode()
    ext = os.path.splitext(fn)[1].lower().lstrip('.')
    ctype = "image/png" if ext == "png" else ("image/jpeg" if ext in ("jpg", "jpeg") else "application/octet-stream")
    body += ("Content-Type: %s\r\n\r\n" % ctype).encode()
    body += content + b"\r\n" + ("--%s--\r\n" % b).encode()
    req = urllib.request.Request(BASE + "/bbs/upload_image.php", data=body,
            headers={**UA, "Content-Type": "multipart/form-data; boundary=" + b,
                     "Referer": BASE + "/bbs/post.php?bankuai=16",
                     "X-Requested-With": "XMLHttpRequest"})
    with op.open(req, timeout=180) as resp:
        j = json.loads(resp.read().decode("utf-8", "ignore"))
    return j


D = r"D:\7tan\7tanAI\7723\img"
years = ['2009', '2010', '2011', '2012', '2013', '2014', '2015']
out = []
for y in years:
    p = os.path.join(D, 'y%s.png' % y)
    j = {"success": False, "url": ""}
    for attempt in range(3):
        try:
            j = upload(p)
            break
        except Exception as e:
            print("  重试", y, repr(e)); time.sleep(3)
    ok = j.get("success")
    url = j.get("url", "")
    full = BASE + "/bbs/" + url.replace("\\", "/")
    out.append({"year": y, "rel": url, "url": full, "bytes": j.get("filesize")})
    print("y%s -> %s  (%s)  ok=%s" % (y, full, j.get("sizeStr"), ok))

json.dump(out, open(r"D:\7tan\7tanAI\7723\_scripts\img_urls.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("写入 img_urls.json")
