# -*- coding: utf-8 -*-
import io
p = r'D:\7tan\7tanAI\7723\老马与7723_素材本.txt'
add = '''

============================================================
九、2026-10-07 ·《7723 版主群像》已发布到主站活动公告版
============================================================
发布平台：7坛主站 https://www.7tan.com/bbs/board/16/ （活动公告 · board 16）
发布账号：老马（7723wap，uid=1）
帖子地址：https://www.7tan.com/bbs/82483/
帖子标题：7723 版主群像 | 当年那些版主，和他们亲手发过的帖子（每人一帖·附原帖链接）
正文文件：D:\\7tan\\7tanAI\\7723\\7723版主群像_UBB.txt（UBB 格式，约 1.76 万字）

■ 内容结构（按老马要求）
  · 收录版主 32 位，每人至少 1 帖（正文节选 + 2 条当年网友回复）
  · 每帖底部挂「▶ 点击查看原帖」按钮，链到 https://www.7tan.com/bbs/{帖号}/
  · 全部取自主站数据库当年真实帖子（2009—2015），未虚构

■ 收录版主（32 位）
  存我（存我小妖）、博丽灵梦、大门、莫小跳、皇甫朝云、小殇、蛋定、沉默、
  小基、不义联盟@Silence、吃屎的小太刀、BLOOD、秋韵物语、那年那月那流殇、
  缘分、陌生人、灰烬、玉碎@田驰、暖夏@叶繁成花、穆清、华夏管家丶莽蛋、
  月光、苏小染、老子只顶触屏、残刃、不修、易（浅）、咸蛋超人、
  凉宫的消失、倾城@神月、清风明月、邪、苍、葬忆

■ 技术备查
  · 站点 UBB 标签（源自 ubb_plus.php）：title / subtitle / caption / divider /
    note / warn / tip / quote / card / badge / btn / url / img=宽 / fold / table / code / hl / b
  · 发帖接口：POST /bbs/post.php  参数 bankuai, title, content, images
  · 改帖接口：POST /bbs/edit.php?id={id}  参数 title, content, fileurl, deleted_files
  · 生成脚本：7723\\_scripts\\build_ubb_mods.py；发布/改帖：publish_mods.py / edit_mods.py
  · 已发布帖的 meta description 仍是旧缓存内容，待站点缓存过期后自动刷新
'''
t = io.open(p, encoding='utf-8').read()
io.open(p, 'w', encoding='utf-8').write(t + add)
print('appended, new len =', len(t + add))
