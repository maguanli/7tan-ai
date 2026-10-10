# -*- coding: utf-8 -*-
import re, io, collections
t = io.open(r'D:\7tan\7tanAI\7723\7723版主群像_UBB.txt', encoding='utf-8').read()
BAD = r'(SB|傻逼|傻B|妈的|你妈|你爹|尼玛|卧槽|菊花|拉屎|色情|生殖器|装逼|屌|疯狗|特么|盗号|串号|精神病|住院|自杀|色狼|贱|妓|裸|奶头|屁股|操|屎)'
c = collections.Counter(re.findall(BAD, t))
lines = ['BAD: %s' % dict(c), 'LEN %d' % len(t), 'btns %d' % t.count('[btn='),
         'titles %d' % t.count('[title]')]
# 列出命中上下文
for m in re.finditer(BAD, t):
    lines.append('  ...' + t[max(0, m.start() - 30):m.start() + 30].replace('\n', ' ') + '...')
io.open(r'D:\7tan\7tanAI\7723\_scripts\_qc.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('ok')
