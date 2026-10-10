# -*- coding: utf-8 -*-
import urllib.request, json, sys, ssl
sys.stdout.reconfigure(encoding='utf-8')
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
def get(u,h=None):
    hh=dict(UA); hh.update(h or {})
    return urllib.request.urlopen(urllib.request.Request(u,headers=hh),timeout=25,context=ctx).read().decode('utf-8','ignore')

bases=['https://api-hot.imsyy.top','https://api.codelife.cc/api/top/list?lang=cn&id=']
for b in bases:
    print("\n#### BASE", b)
    for code,name in [('weibo','微博'),('baidu','百度'),('zhihu','知乎'),('douyin','抖音'),('toutiao','头条'),('bili','B站')]:
        url = b+'/'+code if 'imsyy' in b else b+code
        try:
            if 'imsyy' in b:
                d=json.loads(get(url))
                data=d.get('data') or []
                print(f"-- {name}: {len(data)} 条")
                for i in data[:25]:
                    t=i.get('title') or i.get('name')
                    print('   ', t, '|', i.get('hot') or i.get('desc') or '')
            else:
                d=json.loads(get(url))
            break
        except Exception as e:
            print(f"-- {name} ERR {type(e).__name__} {e}")
