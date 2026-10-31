# -*- coding: utf-8 -*-
import socket, ssl, re, io

p = r"C:\Windows\System32\drivers\etc\hosts"
raw = open(p, "rb").read()
print("hosts 大小", len(raw), "B")
print("前 4 字节", raw[:4])
# UTF-16 检测
if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
    print("编码: UTF-16 (含 BOM)")
    txt = raw.decode("utf-16", "ignore")
else:
    txt = raw.decode("utf-8", "ignore")
hits = [ln for ln in txt.splitlines() if "anfensi" in ln.lower()]
print("anfensi 行数:", len(hits))
for h in hits:
    print("  >", repr(h))

print()
print("=== 用 IP 直连 + Host 头取首页 ===")
ctx = ssl._create_unverified_context()
s = socket.create_connection(("222.246.138.75", 443), timeout=15)
w = ctx.wrap_socket(s, server_hostname="www.anfensi.com")
w.sendall(b"GET / HTTP/1.1\r\nHost: www.anfensi.com\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\nAccept: text/html\r\nConnection: close\r\n\r\n")
buf = b""
while True:
    d = w.recv(65536)
    if not d:
        break
    buf += d
w.close()
head, _, body = buf.partition(b"\r\n\r\n")
print(head.decode("utf-8", "ignore")[:600])
html = body.decode("utf-8", "ignore")
print("body 长度", len(html))
m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
print("title =", m.group(1).strip() if m else "无")
open(r"D:\7tan\7tanAI\_anfensi_home.html", "w", encoding="utf-8").write(html)
for kw in ["安粉丝", "关停", "关闭", "维护", "迁移", "公告", "404", "域名"]:
    print("关键词", kw, "出现", html.count(kw), "次")
