# -*- coding: utf-8 -*-
import io

TXT = r'D:\7tan\7tanAI\7723\老马与7723_素材本.txt'

block = """

============================================================
十一、2026-10-07 ·《7723(7坛) 大事记》已发布到主站活动公告版
============================================================
发布平台：7坛主站 https://www.7tan.com/bbs/board/16/ （活动公告 · board 16）
发布账号：老马（7723wap，uid=1）
帖子地址：https://www.7tan.com/bbs/82484/
帖子标题：7723(7坛) 大事记 | 从一个人的WAP手机游戏网，到一群人的七坛（2009—2015·附原帖链接）
正文文件：D:\\7tan\\7tanAI\\7723\\7723大事记_UBB.txt（UBB 格式，约 3.7 万字）

■ 内容结构（按老马要求）
  · 时间线：2009—2015，共 65 个里程碑（按年排）
    2009·5 ｜ 2010·9 ｜ 2011·5 ｜ 2012·5 ｜ 2013·13 ｜ 2014·22 ｜ 2015·6
  · 每条里程碑 = 平台原文（节选）+ 当年网友回复（最多 5 条，网名/时间/原话）
  · ★ 每条里程碑「底部附原帖链接」：[btn=https://www.7tan.com/bbs/{帖号}/]▶ 点击查看原帖[/btn]
  · 全部取自主站数据库当年真实帖子，未虚构

■ 线上核验（抓实时页面）
  · 标题含「7坛」 ✓
  · 「点击查看原帖」按钮 65 个 ✓
  · 渲染区残留 UBB 标签 0 ✓
  · 关键正文文字（建坛首帖/城堡争霸/青蛙过河/关站帖等）均在 ✓

■ 生成/发布脚本
  · 生成：D:\\7tan\\7tanAI\\7723\\_scripts\\html2ubb.py（从 7723大事记.html 转 UBB，自动挂原帖链接）
  · 发布：D:\\7tan\\7tanAI\\7723\\_scripts\\publish_mods.py（读 publish_conf.json）
  · 核验：verify_dsj.py / verify_dsj2.py / verify_dsj3.py

■ 备查
  · 帖子「正文区域」渲染干净；页面 <script> 内保留 topicContent 原始 UBB（供编辑用），非显示问题
  · 同一版块另有一帖《7723(7坛) 版主群像》https://www.7tan.com/bbs/82483/
"""

with io.open(TXT, 'a', encoding='utf-8') as f:
    f.write(block)
print('appended, new size =', len(io.open(TXT, encoding='utf-8').read()))
