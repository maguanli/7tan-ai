# -*- coding: utf-8 -*-
import io, re
h = io.open(r"D:\7tan\7tanAI\7723\_scripts\_verify_82483.html", encoding="utf-8").read()
res = []
for m in list(re.finditer(re.escape('[title]'), h))[:3]:
    res.append('POS %d\n%s' % (m.start(), re.sub(r'\s+', ' ', h[max(0, m.start() - 300):m.start() + 120])))
res.append('')
for m in list(re.finditer(re.escape('[btn='), h))[:2]:
    res.append('BTN POS %d\n%s' % (m.start(), re.sub(r'\s+', ' ', h[max(0, m.start() - 300):m.start() + 120])))
# 正文容器
i = h.find('class="ubb-title"')
res.append('\n--- first ubb-title context ---')
res.append(re.sub(r'\s+', ' ', h[max(0, i - 500):i + 200]))
io.open(r"D:\7tan\7tanAI\7723\_scripts\_verify2.txt", "w", encoding="utf-8").write('\n'.join(res))
print('ok')
