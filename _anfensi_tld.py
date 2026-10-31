# -*- coding: utf-8 -*-
import subprocess, io, re

out = io.StringIO()
def P(*a):
    out.write(" ".join(str(x) for x in a) + "\n")

def ns(q, srv="223.5.5.5", typ="A"):
    args = ["nslookup"]
    if typ != "A":
        args.append("-type=" + typ)
    args += [q, srv]
    r = subprocess.run(args, capture_output=True, timeout=20)
    o = r.stdout.decode("gbk", "ignore")
    o = re.sub(r"\n\s*\n", "\n", o).strip()
    return o

for d in ["anfensi.cn", "anfensi.com.cn", "anfensi.net", "anfensi.com"]:
    P("=== %s (NS) ===" % d)
    P(ns(d, typ="NS")[:500])
    P()

P("=== anfensi.com MX / TXT ===")
P(ns("anfensi.com", typ="MX")[:300])
P()
P("=== www.anfensi.com CNAME ===")
P(ns("www.anfensi.com", typ="CNAME")[:400])

open(r"D:\7tan\7tanAI\_anfensi_tld.txt", "w", encoding="utf-8").write(out.getvalue())
print("done")
