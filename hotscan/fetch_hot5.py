# -*- coding: utf-8 -*-
import urllib.request, json, sys, ssl, gzip, io
sys.stdout.reconfigure(encoding='utf-8')
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}

def get(u,h=None,ref=None):
    hh=dict(UA); hh.update(h or {})
    hh['Accept-Encoding']='gzip'
    if ref: hh['Referer']=ref
    r=urllib.request.urlopen(urllib.request.Request(u,headers=hh),timeout=25,context=ctx)
    raw=r.read()
    if r.headers.get('Content-Encoding')=='gzip':
        raw=gzip.decompress(raw)
    return raw.decode('utf-8','ignore')

print("="*16,"微博实时热搜","="*16)
try:
    d=json.loads(get('https://weibo.com/ajax/side/hotSearch',ref='https://weibo.com/'))
    for i in d['data']['realtime']:
        tag=''
        if i.get('label_name'): tag='['+i['label_name']+']'
        if i.get('is_ad'): tag+='[广告]'
        print(i.get('realpos'), i['word'], int(i.get('num',0)), tag)
except Exception as e: print('ERR',type(e).__name__,e)

print("\n"+"="*16,"百度热搜","="*16)
try:
    d=json.loads(get('https://top.baidu.com/api/board?platform=wise&tab=realtime',ref='https://top.baidu.com/board'))
    for i in d['data']['cards'][0]['content']:
        w=i.get('word')
        if w:
            print(i.get('index','置顶'), w, '|', (i.get('desc') or '')[:70])
except Exception as e: print('ERR',type(e).__name__,e)
