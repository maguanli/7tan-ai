# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

text = open('detail_146875.html', encoding='utf-8').read()

print('=== 下载相关链接 ===')
for m in re.finditer(r'href="([^"]+)"', text):
    u = m.group(1)
    if 'get.downkuai.com' in u or 'download' in u.lower() or 'apk' in u.lower():
        print(u)

print()
print('=== 版本信息附近文本 ===')
for kw in ['版本', '大小', '更新', '语言', '厂商', '系统', '分类', '包名', '权限']:
    for m in re.finditer(kw + r'[^\n]{0,80}', text):
        s = m.group(0).strip()
        s = re.sub(r'<[^>]+>', '', s)
        if len(s) > 2:
            print(s[:100])
            break

print()
print('=== 下载按钮区域 ===')
m = re.search(r'(下载[^<]{0,20})', text)
m2 = re.findall(r'class="[^"]*down[^"]*"[^>]*>', text)
print(m2[:10])
