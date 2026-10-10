# -*- coding: utf-8 -*-
import urllib.request, json, sys, ssl, gzip
sys.stdout.reconfigure(encoding='utf-8')
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36','Referer':'https://top.baidu.com/board','Accept':'application/json'}
r=urllib.request.urlopen(urllib.request.Request('https://top.baidu.com/api/board?platform=wise&tab=realtime',headers=H),timeout=25,context=ctx)
raw=r.read()
print('len',len(raw),'enc',r.headers.get('Content-Encoding'),'ct',r.headers.get('Content-Type'))
try:
    if r.headers.get('Content-Encoding')=='gzip': raw=gzip.decompress(raw)
except Exception as e: print('gz err',e)
t=raw.decode('utf-8','ignore')
print('head:',t[:300])
try:
    d=json.loads(t)
    for i in d['data']['cards'][0]['content']:
        if i.get('word'): print(i.get('index','置顶'), i['word'],'|',(i.get('desc') or '')[:70])
except Exception as e: print('parse err',e)
