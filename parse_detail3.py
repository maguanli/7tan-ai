# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

text = open('detail_146875.html', encoding='utf-8').read()

print('=== 所有 jump.php / get.downkuai 链接 ===')
for m in re.finditer(r'["\']([^"\']*get\.downkuai[^"\']*)["\']', text):
    print(m.group(1))

print()
print('=== 含 download 的 JS/URL ===')
for m in re.finditer(r'[^"\']*(?:download|Download)[^"\']*', text):
    s = m.group(0).strip()
    if len(s) > 5 and len(s) < 200:
        print(s)

print()
print('=== 下载按钮附近 300 字符 ===')
idx = text.find('class="down"')
if idx > 0:
    print(text[idx-500:idx+500])
