# -*- coding: utf-8 -*-
"""抓取微信公众号文章正文"""
import urllib.request, re, html, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

URL = 'https://mp.weixin.qq.com/s/QKMiWu2rtcCRJA3N37YvYw'

req = urllib.request.Request(URL, headers={
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.40'
})
page = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')

# 标题
m = re.search(r'<h1[^>]*id="activity-name"[^>]*>(.*?)</h1>', page, re.S)
title = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else 'N/A'

# 公众号名
m2 = re.search(r'id="js_name"[^>]*>(.*?)</a>', page, re.S)
acc = re.sub(r'<[^>]+>', '', m2.group(1)).strip() if m2 else 'N/A'

# 发布时间
m4 = re.search(r'var createTime = \'([^\']+)\'', page) or re.search(r'publish_time[^>]*>([^<]+)<', page)
ptime = m4.group(1).strip() if m4 else 'N/A'

# 正文
m3 = re.search(r'<div[^>]*id="js_content"[^>]*>(.*)', page, re.S)
body = m3.group(1) if m3 else ''
# 截断到正文结束标记
end = body.find('id="js_tags"')
if end > 0:
    body = body[:end]
body = re.sub(r'<script.*?</script>', '', body, flags=re.S)
body = re.sub(r'<style.*?</style>', '', body, flags=re.S)
body = re.sub(r'<br[^>]*>', '\n', body)
body = re.sub(r'</p>', '\n', body)
body = re.sub(r'</section>', '\n', body)
body = re.sub(r'</h[1-6]>', '\n', body)
body = re.sub(r'<[^>]+>', '', body)
body = html.unescape(body).replace('\xa0', ' ')
body = re.sub(r'[ \t]+', ' ', body)
body = re.sub(r'\n{3,}', '\n\n', body).strip()

out = []
out.append('===标题=== ' + title)
out.append('===公众号=== ' + acc)
out.append('===发布时间=== ' + ptime)
out.append('===正文长度=== %d 字' % len(body))
out.append('===正文===')
out.append(body[:6000])
print('\n'.join(out))

# 保存全文
with open(r'D:\7tan\7tanAI\data\wx_article_mortgage.txt', 'w', encoding='utf-8') as f:
    f.write(title + '\n' + acc + '\n' + ptime + '\n\n' + body)
print('\n[全文已保存] D:\\7tan\\7tanAI\\data\\wx_article_mortgage.txt')
