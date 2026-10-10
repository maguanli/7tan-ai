# -*- coding: utf-8 -*-
import io
p = r'D:\7tan\7tanAI\7723\老马与7723_素材本.txt'
s = io.open(p, encoding='utf-8').read()
add = """

【十】2026-10-07 《7723(7坛) 版主群像》帖子修订（活动公告 board 16 · 帖号 82483）
- 标题：7723 版主群像 → 7723(7坛) 版主群像
- 版主顺序：把「小基（Beta2游侠）」移到第二位（存我之后）
  现行顺序：存我 → 小基 → 博丽灵梦 → 大门 → 莫小跳 → 皇甫朝云 → 小殇 → …
- 去掉每位版主名称前的数字序号（原为 01 · 02 · …）
- 线上核验：标题含 7坛 ✓ ｜ 无数字序号 ✓ ｜ 32 个原帖按钮 ✓ ｜ 版主顺序正确 ✓
"""
io.open(p, 'w', encoding='utf-8').write(s.rstrip() + add)
print('memo appended, lines', io.open(p, encoding='utf-8').read().count('\n') + 1)
