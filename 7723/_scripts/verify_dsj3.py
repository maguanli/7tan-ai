# -*- coding: utf-8 -*-
"""确认正文「已渲染的部分」里有关键文字（排除 script 原始源码）"""
import re, urllib.request, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PID = '82484'
req = urllib.request.Request('https://www.7tan.com/bbs/%s/' % PID,
                             headers={'User-Agent': 'Mozilla/5.0'})
h = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')

# 把所有 <script>...</script> 移除后，再看剩下（即真正渲染出来的 HTML）
stripped = re.sub(r'<script\b.*?</script>', '', h, flags=re.S)
stripped = re.sub(r'<style\b.*?</style>', '', stripped, flags=re.S)

checks = [
    '7723(7坛) 大事记',
    '从一个人的 WAP 手机游戏网',
    '建坛首帖',
    '抗日英雄传之任务攻略',
    '告诉大家一个遗憾的消息',
    '▶ 点击查看原帖',
    '你是我永远的公主',   # 2009 情感帖正文里的句子
    '城堡争霸',           # 2014
    '青蛙过河',           # 2014 html5
    '生是7坛人',          # 2015 回复
]
print('=== 渲染后正文关键文字检查（script/style 已剔除）===')
for c in checks:
    print(('  ✓ ' if c in stripped else '  ✗ ') + c)

print('渲染区残留 UBB 标签 :', re.findall(r'\[(title|subtitle|caption|note|quote|btn|divider)[^\]]*\]', stripped)[:5])
print('渲染区 [btn= 链接数 :', len(re.findall(r'/bbs/\d+/', stripped)))
