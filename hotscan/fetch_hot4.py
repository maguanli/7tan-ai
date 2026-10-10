# -*- coding: utf-8 -*-
import urllib.request, json, sys, ssl
sys.stdout.reconfigure(encoding='utf-8')
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
def get(u,h=None):
    hh=dict(UA); hh.update(h or {})
    return urllib.request.urlopen(urllib.request.Request(u,headers=hh),timeout=25,context=ctx).read().decode('utf-8','ignore')

base='https://api-hot.imsyy.top'
for code,name in [('weibo','微博'),('baidu','百度'),('zhihu','知乎'),('douyin','抖音'),('toutiao','头条'),('bilibili','B站'),('kuaishou','快手'),('36kr','36氪')]:
    try:
        d=json.loads(get(base+'/'+code))
        data=d.get('data') or []
        print(f"\n===== {name} ({len(data)}条) =====")
        for i in data[:25]:
            print('  ', i.get('title') or i.get('name'), '|', i.get('hot') or i.get('desc') or '')
    except Exception as e:
        print(f"\n===== {name} ERR {type(e).__name__}: {e}")
