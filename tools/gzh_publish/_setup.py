# -*- coding: utf-8 -*-
"""创建公众号发布套件：复制核心脚本/文章/封面到软件目录"""
import os, shutil

src_dir = r'D:\用户目录\下载\新建文件夹 123\11'
dst_dir = r'D:\7tan\7tanAI\tools\gzh_publish'
os.makedirs(dst_dir, exist_ok=True)

files = [
    ('region_ocr.py', 'region_ocr.py'),
    ('公众号爆款文章_最终版.txt', 'article_final.txt'),
    ('公众号爆款文章_7Tan发布游戏.txt', 'article_7tan_games.txt'),
    ('公众号封面_横图_900x383.png', 'cover_900x383.png'),
]
for src, dst in files:
    s = os.path.join(src_dir, src)
    d = os.path.join(dst_dir, dst)
    if os.path.exists(s):
        shutil.copy2(s, d)
        print(f'OK  {src} -> {dst}  ({os.path.getsize(d)} bytes)')
    else:
        print(f'MISS {src}')

# 生成发布流程说明
readme = """# 公众号发布套件（gzh_publish）

生成时间：2026-08-06
用途：7Tan AI 发布微信公众号爆款文章的标准工具集

## 文件说明
- region_ocr.py      区域裁剪OCR工具（读取微信文章阅读量，避免CPU100%）
- article_final.txt  公众号爆款文章·最终版（标题A/B/C + 摘要 + 正文）
- article_7tan_games.txt  基于7tan已发布游戏的版本（导流用）
- cover_900x383.png  封面图（横图 900x383）

## 发布流程（经验总结）
1. 爆款调研：电脑微信搜索 -> 文章 -> 最热 -> 逐篇打开，用 region_ocr.py 框选底部阅读量
   只保留 10万+ 的真爆款，逐字拆解标题公式/开头钩子/正文结构
2. 标题公式：痛点/场景 + 数字(4款/5款) + 类型 + 情绪词(太上头/停不下来)
3. 正文套路：立人设 -> 痛点共鸣 -> 编号清单(每款=名称+一句话亮点+具体数据) -> 互动结尾
4. 发布：微信公众平台 -> 图文消息 -> 填标题/作者/正文 -> 上传封面 -> 填摘要
   -> 勾选原创声明 -> 保存草稿 -> 发表
5. 发表按钮位置：保存草稿右侧第3个按钮（有"发表"字样）
6. 变现：赞赏 + 流量主 + 原文链接导流 7tan 站

## 注意事项
- 文章数据必须来自7tan数据库真实游戏信息，绝不编造评分/下载量
- 封面图片建议 900x383（横图）
- 摘要 120 字内（转发卡片显示）
"""
with open(os.path.join(dst_dir, 'README.md'), 'w', encoding='utf-8') as f:
    f.write(readme)
print('OK  README.md')
print('DONE')
