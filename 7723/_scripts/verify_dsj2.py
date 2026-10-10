# -*- coding: utf-8 -*-
"""定位残留 UBB 标签到底出现在页面什么位置"""
import re, urllib.request, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PID = '82484'
req = urllib.request.Request('https://www.7tan.com/bbs/%s/' % PID,
                             headers={'User-Agent': 'Mozilla/5.0'})
h = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')

# 1) 正文区域（帖子内容）通常在 article / .post / .content 里
m = re.search(r'<(article|div)[^>]*class="[^"]*(?:post|content|article|thread)[^"]*"[^>]*>(.*?)</\1>', h, re.S)
body = m.group(2) if m else ''
print('正文区域长度 :', len(body))
print('正文内残留标签 :', re.findall(r'\[(title|subtitle|caption|note|quote|btn|divider)[^\]]*\]', body)[:10])

# 2) 检查是否有 textarea / script 模板 保存了原始 UBB
for tag in ['textarea', 'script']:
    cnt = len(re.findall(r'<%s\b' % tag, h))
    print('<%s> 数量 : %d' % (tag, cnt))

# 3) 全局残留分布：打印每个残留前 40 字符上下文
resid = list(re.finditer(r'\[(?:title|subtitle|caption|note|quote|btn|divider)[^\]]*\]', h))
print('全局残留实例前 6 条上下文:')
for mm in resid[:6]:
    s = max(0, mm.start() - 40)
    print('  ...', repr(h[s:mm.end() + 20]))

# 4) 判断残留是否落在 <style> 或 <script> 内
styles = [(s.start(), s.end()) for s in re.finditer(r'<style\b.*?</style>', h, re.S)]
scripts = [(s.start(), s.end()) for s in re.finditer(r'<script\b.*?</script>', h, re.S)]
def in_ranges(pos, ranges):
    return any(a <= pos < b for a, b in ranges)
ins = sum(1 for mm in resid if in_ranges(mm.start(), styles))
insc = sum(1 for mm in resid if in_ranges(mm.start(), scripts))
print('落在 <style> 内的残留 :', ins)
print('落在 <script> 内的残留 :', insc)
print('落在正文外的残留 :', len(resid) - ins - insc)
