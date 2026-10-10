# -*- coding: utf-8 -*-
import urllib.request, json, sys, ssl
sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
def get(u,h=None):
    hh=dict(UA); hh.update(h or {})
    return urllib.request.urlopen(urllib.request.Request(u,headers=hh),timeout=25,context=ctx).read().decode('utf-8','ignore')

print("="*18,"百度热搜","="*18)
try:
    d=json.loads(get('https://top.baidu.com/api/board?platform=wise&tab=realtime'))
    for i in d['data']['cards'][0]['content']:
        if 'word' in i:
            print(i.get('index','置顶'), i['word'], '|', (i.get('desc') or '')[:60])
except Exception as e: print('ERR',e)

print("\n"+"="*18,"微博热搜","="*18)
for api in ['https://api.vvhan.com/api/hotlist/wbHot',
            'https://api.vvhan.com/api/hotlist/wbHot?type=realTime']:
    try:
        d=json.loads(get(api))
        for i in d.get('data',[])[:40]:
            print(i.get('hot'), i.get('title'))
        break
    except Exception as e: print('ERR',api,e)

print("\n"+"="*18,"快手热榜","="*18)
try:
    d=json.loads(get('https://api.vvhan.com/api/hotlist/ksHot'))
    for i in d.get('data',[])[:30]: print(i.get('hot'), i.get('title'))
except Exception as e: print('ERR',e)

print("\n"+"="*18,"抖音热点榜(第三方)","="*18)
try:
    d=json.loads(get('https://api.vvhan.com/api/hotlist/douyinHot'))
    for i in d.get('data',[])[:30]: print(i.get('hot'), i.get('title'))
except Exception as e: print('ERR',e)
