# -*- coding: utf-8 -*-
import re, collections, json
import urllib.request, gzip, io

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    r = urllib.request.urlopen(req, timeout=30)
    data = r.read()
    if r.headers.get('Content-Encoding') == 'gzip' or data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    return data.decode('utf-8', 'replace')

idx = get('https://www.7tan.com/sitemap.xml')
subs = re.findall(r'<loc>(.*?)</loc>', idx)
print('索引内子图数:', len(subs))
for s in subs:
    print('  ', s)

total_entries = 0          # <url> 条目数
total_loc = 0              # <loc> 出现次数
cnt_entries = collections.Counter()   # 按条目
cnt_loc = collections.Counter()       # 按loc出现次数

per_sub = []
for s in subs:
    xml = get(s)
    locs       = re.findall(r'<loc>(.*?)</loc>', xml)
    lastmods   = re.findall(r'<lastmod>(.*?)</lastmod>', xml)
    n_url_tag  = len(re.findall(r'<url>', xml))
    per_sub.append((s, n_url_tag, len(locs), len(lastmods)))
    total_entries += n_url_tag
    total_loc += len(locs)
    for m in lastmods:
        cnt_entries[m] += 1
    # 按 loc 出现次数：把 lastmod 挂到 loc 上（简化：顺序配对）
    print(f'  {s.split("/")[-1]}: <url>={n_url_tag}  <loc>={len(locs)}  <lastmod>={len(lastmods)}')

print()
print('=== 合计 ===')
print('<url> 条目总数:', total_entries)
print('<loc> 出现总数:', total_loc)
print('<lastmod> 总数 :', sum(cnt_entries.values()))

print()
print('=== lastmod 分布（按出现次数）===')
for k, v in cnt_entries.most_common():
    print(f'  {k}: {v}  ({v*100.0/sum(cnt_entries.values()):.1f}%)')

print()
print('=== 单日 >=100 的日期 ===')
for k, v in sorted(cnt_entries.items()):
    if v >= 100:
        print(f'  {k}: {v}')

# 计算"其余9月各日"到底是多少（排除最大那天、排除当日）
today = '2026-10-29'
maxday = cnt_entries.most_common(1)[0][0]
rest = sum(v for k, v in cnt_entries.items() if k not in (maxday, today))
print()
print('最大日:', maxday, cnt_entries[maxday])
print('当日:', today, cnt_entries[today])
print('其余（排除这两者）:', rest)
print('校验 最大日+当日+其余 =', cnt_entries[maxday] + cnt_entries[today] + rest, ' 应等于', sum(cnt_entries.values()))

json.dump({'per_sub': per_sub, 'total_url': total_entries, 'total_loc': total_loc,
           'dist': dict(cnt_entries)}, open(r'D:\7tan\7tanAI\_lastmod_stat.json','w',encoding='utf-8'),
          ensure_ascii=False, indent=1)
