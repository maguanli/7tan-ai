# -*- coding: utf-8 -*-
import io
t = io.open(r'D:\7tan\7tanAI\7723\7723版主群像_UBB.txt', encoding='utf-8').read()
print('backslash count:', t.count('\\'))
i = t.find('大喊道')
print(repr(t[i - 20:i + 60]))
print('ascii quotes:', t.count('"'))
