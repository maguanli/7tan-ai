# -*- coding: utf-8 -*-
import urllib.request, json, sys, ssl
sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}

def get(url, headers=None):
    h = dict(UA)
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=25, context=ctx).read().decode('utf-8', 'ignore')

print("="*20, "百度热搜", "="*20)
try:
    d = json.loads(get('https://top.baidu.com/api/board?platform=wise&tab=realtime'))
    for i in d['data']['cards'][0]['content']:
        print(i.get('index','置顶'), i['word'], '|', (i.get('desc','') or '')[:70])
except Exception as e:
    print('ERR', e)

print("\n" + "="*20, "抖音热榜", "="*20)
try:
    d = json.loads(get('https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/'))
    for i in d.get('word_list', []):
        print(int(i['hot_value']), i['word'])
except Exception as e:
    print('ERR', e)

print("\n" + "="*20, "知乎热榜", "="*20)
try:
    d = json.loads(get('https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50'))
    for i in d['data']:
        print(i['target']['title'], '|', (i.get('detail_text','') or ''))
except Exception as e:
    print('ERR', e)

print("\n" + "="*20, "头条热榜", "="*20)
try:
    d = json.loads(get('https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc'))
    for i in d.get('data', []):
        print(i.get('HotValue'), i.get('Title'), '|', i.get('Url',''))
except Exception as e:
    print('ERR', e)

print("\n" + "="*20, "B站热门", "="*20)
try:
    d = json.loads(get('https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1', {'Referer':'https://www.bilibili.com'}))
    for i in d['data']['list']:
        print(i['stat']['view'], i['title'])
except Exception as e:
    print('ERR', e)

print("\n" + "="*20, "微博热搜(第三方)", "="*20)
try:
    d = json.loads(get('https://api.vvhan.com/api/hotlist/wbHot'))
    for i in d.get('data', [])[:50]:
        print(i.get('hot'), i.get('title'))
except Exception as e:
    print('ERR', e)
