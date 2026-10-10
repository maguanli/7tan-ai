# -*- coding: utf-8 -*-
r"""向 7723大事记_配图_UBB.txt 末尾追加「现在」结尾节（幂等：已存在则不重复写）"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
FP = r"D:\7tan\7tanAI\7723\7723大事记_配图_UBB.txt"
s = io.open(FP, encoding='utf-8').read()
print("追加前行数:", s.count("\n") + 1)
if "[title]现在[/title]" in s:
    print("已存在「现在」节，跳过。")
else:
    tail = """

[divider]
[title]现在[/title]

[b]如今，当年那群人又聚了回来。[/b]
[caption]7坛游戏社区（7tan.com）· 2026 年 4 月 11 日正式上线[/caption]
当年的 7723，域名换成了 7tan.com。如今访问 https://www.7tan.com/ ——「7坛游戏社区」，于 2026 年 4 月 11 日正式上线，做的还是当年那件事：下游戏、聊游戏、一群人。
[btn=https://www.7tan.com/]▶ 访问 7坛游戏社区（7tan.com）[/btn]
"""
    s = s.rstrip("\n") + tail
    io.open(FP, "w", encoding='utf-8').write(s)
    print("已追加「现在」节。")
print("追加后行数:", s.count("\n") + 1)
print("校验 含[title]现在[/title]:", "[title]现在[/title]" in s)
print("校验 含上线日期:", "2026 年 4 月 11 日" in s)
print("---- 末尾 300 字 ----")
print(s[-300:])
