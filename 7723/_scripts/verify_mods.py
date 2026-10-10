# -*- coding: utf-8 -*-
import io, re
t = io.open(r'D:\7tan\7tanAI\7723\7723版主群像_UBB.txt', encoding='utf-8').read()
ms = re.findall(r'\[title\]([^\[]+)\[/title\]', t)
print('lines', t.count('\n') + 1)
print('title_count', len(ms))
for i, x in enumerate(ms[:6]):
    print(i + 1, x)
print('num_left', len(re.findall(r'\[title\]\d+', t)))
print('xiaoji_pos', [i + 1 for i, x in enumerate(ms) if '小基' in x])
print('cunwo_pos', [i + 1 for i, x in enumerate(ms) if '存我' in x])
