# -*- coding: utf-8 -*-
import urllib.request, re, ssl, io
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
def get(u):
    req = urllib.request.Request(u, headers={'User-Agent':'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=30, context=ctx).read().decode('utf-8','ignore')
def text(h):
    h = re.sub(r'(?is)<(script|style).*?</\1>', ' ', h)
    t = re.sub(r'(?s)<[^>]+>', ' ', h)
    return re.sub(r'\s+', ' ', t)
out = io.open(r'D:\7tan\7tanAI\7723\_scripts\_fetch_out2.txt','w',encoding='utf-8')
urls = ['https://www.7tan.com/', 'https://www.7tan.com/baike/', 'https://www.7tan.com/web/map.htm', 'https://www.7tan.com/web/lcwm.htm']
for u in urls:
    try:
        t = text(get(u))
        out.write('==== %s\n' % u)
        out.write(t[:1200] + '\n')
        for kw in ['上线','始于','运行','成立','2021','2022','2023','2024','2025','2026','备案','柒']:
            for m in re.finditer(kw, t):
                i=m.start(); out.write('  [%s] ...%s...\n' % (kw, t[max(0,i-30):i+50]))
        out.write('\n')
    except Exception as e:
        out.write('ERR %s %s\n' % (u, e))
out.close(); print('ok')
