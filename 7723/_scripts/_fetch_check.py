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

out = io.open(r'D:\7tan\7tanAI\7723\_scripts\_fetch_out.txt','w',encoding='utf-8')
urls = [
 'https://www.7tan.com/bbs/board/16_ding/',
 'https://www.7tan.com/bbs/board/16/',
 'https://www.7tan.com/bbs/board/16_2/',
]
for u in urls:
    try:
        h = get(u); t = text(h)
        out.write('===== %s len=%d\n' % (u, len(h)))
        out.write('HEAD: %s\n' % t[:600])
        # find post titles: pattern looks like "标题 作者 日期"
        for kw in ['上线','正式','开站','2021','备案','ICP','柒贰叁叁','公告','置顶']:
            for m in re.finditer(kw, t):
                i=m.start()
                out.write('  [%s] ...%s...\n' % (kw, t[max(0,i-50):i+70]))
        out.write('\n')
    except Exception as e:
        out.write('ERR %s %s\n' % (u, e))
out.close()
print('done')
