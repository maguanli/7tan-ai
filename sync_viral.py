# -*- coding: utf-8 -*-
import io

src_path = r"tools/viral_writer/tools.py"
dst_path = r"data/plugins/viral_writer/tools.py"
src = io.open(src_path, encoding="utf-8", newline="").read()
dst = io.open(dst_path, encoding="utf-8", newline="").read()

# 源码（强化版）中 viral_write 的第1~11条（到 12. 输出铁律 之前，rstrip 去尾部空白）
a = src.find('f"1. 去AI痕迹（最高优先级铁律')
b = src.find('f"\\n12. 输出铁律', a)
assert a != -1 and b != -1, ("src anchor fail", a, b)
new_block = src[a:b].rstrip()
assert new_block.endswith('"'), "new_block must end with quote"
print("new_block len:", len(new_block))
print("NEW ends:", repr(new_block[-90:]))

# 运行副本（旧版）中 viral_write 的第1~11条
c = dst.find('f"1. 结构：五段式')
d = dst.find('不给自己贴「总结」标签"')
assert c != -1 and d != -1, ("dst anchor fail", c, d)
old_block = dst[c:d + len('不给自己贴「总结」标签"')]
print("old_block len:", len(old_block))
print("OLD ends:", repr(old_block[-60:]))

out = dst[:c] + new_block + dst[d + len('不给自己贴「总结」标签"'):]
io.open(dst_path, "w", encoding="utf-8", newline="").write(out)
print("written, new total len:", len(out))
