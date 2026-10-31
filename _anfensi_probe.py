# -*- coding: utf-8 -*-
import socket, ssl, time

ips = ["222.246.138.75", "110.80.150.98", "113.125.215.63"]
for ip in ips:
    for port in (80, 443):
        try:
            s = socket.create_connection((ip, port), timeout=8)
            s.settimeout(8)
            if port == 80:
                s.sendall(b"GET / HTTP/1.1\r\nHost: www.anfensi.com\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n")
                data = s.recv(400)
                print(ip, port, "OPEN ->", data[:120])
            else:
                ctx = ssl._create_unverified_context()
                w = ctx.wrap_socket(s, server_hostname="www.anfensi.com")
                print(ip, port, "OPEN TLS ->", w.version())
            s.close()
        except Exception as e:
            print(ip, port, "FAIL", type(e).__name__, str(e)[:80])
