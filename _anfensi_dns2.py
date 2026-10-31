# -*- coding: utf-8 -*-
import subprocess, re, io

out = io.StringIO()
def P(*a):
    out.write(" ".join(str(x) for x in a) + "\n")

r = subprocess.run(["ipconfig", "/all"], capture_output=True)
txt = r.stdout.decode("gbk", "ignore")
# 抓 IPv4 形式
dns = re.findall(r"(?:DNS 服务器|DNS Servers)[^\n]*:\s*((?:\d{1,3}\.){3}\d{1,3})", txt)
P("IPv4 DNS 服务器:", dns)
P()
servers = list(dict.fromkeys(dns + ["223.5.5.5", "119.29.29.29", "114.114.114.114", "8.8.8.8", "1.1.1.1"]))
for srv in servers:
    try:
        rr = subprocess.run(["nslookup", "www.anfensi.com", srv], capture_output=True, timeout=15)
        o = rr.stdout.decode("gbk", "ignore")
        ips = re.findall(r"(?:^|\s)((?:\d{1,3}\.){3}\d{1,3})\s*$", o, re.M)
        ips = [x for x in ips if x != srv]
        flag = ""
        if "127.0.0.1" in o:
            flag = "  <== 返回 127.0.0.1 (被劫持/屏蔽)"
        if "timed out" in o.lower() or "超时" in o:
            flag += "  (超时)"
        P("%-16s -> %s%s" % (srv, ips[:4] if ips else "无结果", flag))
    except Exception as e:
        P("%-16s -> 出错 %s" % (srv, e))
open(r"D:\7tan\7tanAI\_anfensi_dns2.txt", "w", encoding="utf-8").write(out.getvalue())
print("done")
