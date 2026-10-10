# -*- coding: utf-8 -*-
import urllib.request, json, sys, ssl
sys.stdout.reconfigure(encoding='utf-8')
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36','Referer':'https://top.baidu.com/board'}
d=json.loads(urllib.request.urlopen(urllib.request.Request('https://top.baidu.com/api/board?platform=wise&tab=realtime',headers=H),timeout=25,context=ctx).read().decode('utf-8','ignore'))
def walk(node, out):
    if isinstance(node, dict):
        if 'word' in node and isinstance(node.get('word'), str): out.append(node)
        for v in node.values(): walk(v, out)
    elif isinstance(node, list):
        for v in node: walk(v, out)
out=[]; walk(d.get('data',{}).get('cards',[]), out)
seen=set()
for i in out:
    w=i['word']
    if w in seen: continue
    seen.add(w)
    print(i.get('index','置顶'), w, '|', (i.get('desc') or '')[:70])
