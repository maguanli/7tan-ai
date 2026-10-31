# -*- coding: utf-8 -*-
import subprocess, re, socket, io

out = io.StringIO()
def P(*a):
    out.write(" ".join(str(x) for x in a) + "\n")

r = subprocess.run(["ipconfig", "/all"], capture_output=True)
txt = r.stdout.decode("gbk", "ignore")
dns = re.findall(r"(?:DNS 服务器|DNS Servers)[^\n]*:\s*([0-9a-fA-F\.\:]+)", txt)
P("本机配置的 DNS 服务器:", dns)

# 逐个查询
for srv in dns:
    try:
        rr = subprocess.run(["nslookup", "www.anfensi.com", srv], capture_output=True, timeout=20)
        o = rr.stdout.decode("gbk", "ignore")
        ips = re.findall(r"(?:Address|Addresses):\s*([0-9\.\s]+)", o)
        P("查询 %s -> %s" % (srv, [i.strip() for i in ips][:5]))
        if "127.0.0.1" in o:
            P("   !! 该 DNS 返回 127.0.0.1")
        if "timed out" in o.lower() or "超时" in o:
            P("   !! 超时")
    except Exception as e:
        P("查询 %s 出错 %s" % (srv, e))

P("")
P("socket 解析结果:", socket.gethostbyname_ex("www.anfensi.com"))
P("")
# 对比一个正常站点
for d in ["www.7tan.com", "www.baidu.com", "www.anfensi.com"]:
    try:
        P(d, "->", socket.gethostbyname(d))
    except Exception as e:
        P(d, "-> 失败", e)
open(r"D:\7tan\7tanAI\_anfensi_dns.txt", "w", encoding="utf-8").write(out.getvalue())
print("done")
