# -*- coding: utf-8 -*-
import socket, ssl, re, json, io
from collections import Counter

out = io.StringIO()
def P(*a):
    out.write(" ".join(str(x) for x in a) + "\n")

ctx = ssl._create_unverified_context()
s = socket.create_connection(("222.246.138.75", 443), timeout=20)
w = ctx.wrap_socket(s, server_hostname="www.anfensi.com")
w.sendall(b"GET / HTTP/1.1\r\nHost: www.anfensi.com\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\nAccept: text/html,application/xhtml+xml\r\nConnection: close\r\n\r\n")
buf = b""
while True:
    d = w.recv(65536)
    if not d:
        break
    buf += d
w.close()
head, _, body = buf.partition(b"\r\n\r\n")
open(r"D:\7tan\7tanAI\_anfensi_home.html", "wb").write(body)
P("HTTP 头:")
P(head.decode("utf-8", "ignore"))
P("")
P("body 字节数:", len(body))

# 编码判定
for enc in ("utf-8", "gb18030"):
    t = body.decode(enc, "ignore")
    chi = sum(1 for c in t if "\u4e00" <= c <= "\u9fff")
    P("按 %s 解码：汉字 %d 个" % (enc, chi))

t = body.decode("gb18030", "ignore")
m = re.search(r"<title>(.*?)</title>", t, re.S | re.I)
P("")
P("TITLE:", (m.group(1).strip() if m else "无")[:120])
m2 = re.search(r'name="description"\s+content="(.*?)"', t, re.S | re.I)
P("DESC:", (m2.group(1)[:200] if m2 else "无"))
m3 = re.search(r'charset=["\']?([\w-]+)', t, re.I)
P("页面声明编码:", m3.group(1) if m3 else "无")
P("")
for kw in ["安粉丝", "关停", "关闭", "维护", "迁移", "公告", "停机", "暂停", "关站", "已停止"]:
    P("关键词 %s : %d 次" % (kw, t.count(kw)))
P("")
alld = re.findall(r"20\d\d-\d\d-\d\d", t)
P("页面里的日期串 Top10:", Counter(alld).most_common(10))
P("")
# 链接数量、是否有大量游戏下载页
hrefs = re.findall(r'href="([^"]+)"', t)
P("a 标签数:", len(hrefs))
P("站内相对链接样例:", [h for h in hrefs if h.startswith("/")][:8])
open(r"D:\7tan\7tanAI\_anfensi_report.txt", "w", encoding="utf-8").write(out.getvalue())
print("done")
