# -*- coding: utf-8 -*-
"""按老马要求修改：① 标题加 (7坛) ② 小基(Beta2游侠) 移到第二位(存我之后) ③ 去掉版主名称前的数字序号"""
import io, json

BP = r'D:\7tan\7tanAI\7723\_scripts\build_ubb_mods.py'
s = io.open(BP, encoding='utf-8').read()
orig = s

# ① 标题
s = s.replace('[title]7723 版主群像[/title]', '[title]7723(7坛) 版主群像[/title]')

# ③ 去掉数字序号
s = s.replace("'[title]%02d · %s[/title]' % (i, disp)", "'[title]%s[/title]' % disp")

# ② 小基 移到 存我 之后（第二位）
XA = "    ('小基（Beta2游侠）', '聊天灌水版主', '39201'),\n"
s = s.replace(
    "    ('存我（存我小妖）', '核心管理 · 首任副站长 · 评论组组长', '5470'),\n    ('博丽灵梦', '版主', '11539'),\n",
    "    ('存我（存我小妖）', '核心管理 · 首任副站长 · 评论组组长', '5470'),\n" + XA + "    ('博丽灵梦', '版主', '11539'),\n",
)
s = s.replace(
    "    ('沉默（综合组）', '综合组版主', '9727'),\n" + XA + "    ('不义联盟@Silence', '安卓版主', '12016'),\n",
    "    ('沉默（综合组）', '综合组版主', '9727'),\n    ('不义联盟@Silence', '安卓版主', '12016'),\n",
)

io.open(BP, 'w', encoding='utf-8').write(s)
print('build script changed:', s != orig)

# ④ 发布配置里的帖子标题
CP = r'D:\7tan\7tanAI\7723\_scripts\publish_conf.json'
conf = json.load(io.open(CP, encoding='utf-8'))
conf['title'] = '7723(7坛) 版主群像 | 当年那些版主，和他们亲手发过的帖子（每人一帖·附原帖链接）'
io.open(CP, 'w', encoding='utf-8').write(json.dumps(conf, ensure_ascii=False, indent=2))
print('conf title:', conf['title'])
