# -*- coding: utf-8 -*-
import re, socket

p = r"C:\Windows\System32\drivers\etc\hosts"
try:
    txt = open(p, "r", encoding="utf-8", errors="ignore").read()
except Exception as e:
    txt = ""
    print("read hosts ERR", e)

hits = [ln for ln in txt.splitlines() if "anfensi" in ln.lower()]
print("hosts 文件中 anfensi 相关行:", hits if hits else "无")

# 看看本机把 www.anfensi.com 解析成什么
for h in ["www.anfensi.com", "anfensi.com"]:
    try:
        print(h, "->", socket.gethostbyname_ex(h))
    except Exception as e:
        print(h, "解析失败", type(e).__name__, e)
