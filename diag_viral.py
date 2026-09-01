# -*- coding: utf-8 -*-
import io
path = r"data/plugins/viral_writer/tools.py"
s = io.open(path, encoding="utf-8").read()
i = s.find('f"1. 结构：五段式')
j = s.find('不给自己贴「总结」标签"')
print("start_anchor_pos:", i)
print("end_anchor_pos:", j)
print("---- start repr ----")
print(repr(s[i:i+200]))
print("---- end repr ----")
print(repr(s[j-100:j+30]))
print("---- total len ----", len(s))
