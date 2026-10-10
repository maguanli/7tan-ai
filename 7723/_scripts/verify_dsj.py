# -*- coding: utf-8 -*-
"""核验线上《7723(7坛) 大事记》帖子渲染"""
import re, urllib.request, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PID = '82484'
req = urllib.request.Request('https://www.7tan.com/bbs/%s/' % PID,
                             headers={'User-Agent': 'Mozilla/5.0'})
h = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')

t = re.search(r'<title>(.*?)</title>', h, re.S)
print('TITLE =', t.group(1).strip() if t else None)
print('标题含 7坛 :', ('7坛' in h))
print('/bbs/NNN/ 链接出现次数 :', len(re.findall(r'/bbs/\d+/', h)))
btns = re.findall(r'>\s*▶ 点击查看原帖\s*<', h)
print('「点击查看原帖」按钮数 :', len(btns))
print('年份小节数 :', len(re.findall(r'2009|2010|2011|2012|2013|2014|2015', h)))
resid = re.findall(r'\[(title|subtitle|caption|note|quote|btn|divider)[^\]]*\]', h)
print('残留 UBB 标签 :', resid[:10], '共', len(resid))
print('含「告诉大家一个遗憾的消息」:', '遗憾的消息' in h)
