# -*- coding: utf-8 -*-
import socket, urllib.request, json

def whois43(server, q, timeout=12):
    try:
        s = socket.create_connection((server, 43), timeout=timeout)
        s.sendall((q + "\r\n").encode())
        buf = b""
        while True:
            d = s.recv(4096)
            if not d:
                break
            buf += d
        s.close()
        return buf.decode("utf-8", "ignore")
    except Exception as e:
        return "ERR %s: %s" % (type(e).__name__, e)

def rdap(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/rdap+json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "ignore")[:3000]
    except Exception as e:
        return None, "ERR %s: %s" % (type(e).__name__, e)

print("=== 1. whois.cnnic.net.cn  anfensi.cn ===")
print(whois43("whois.cnnic.net.cn", "anfensi.cn")[:1500])
print()
print("=== 2. whois.verisign-grs.com  anfensi.com ===")
print(whois43("whois.verisign-grs.com", "=anfensi.com")[:1500])
print()
for u in ["https://rdap.org/domain/anfensi.cn",
          "https://rdap.verisign.com/com/v1/domain/anfensi.com"]:
    st, body = rdap(u)
    print("=== RDAP", u, "status=", st, "===")
    print(body[:1500])
    print()
