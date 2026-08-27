# -*- coding: utf-8 -*-
"""从已发布的 HTML 中提取正文（去掉 base64），便于定位修改点"""
import re, io, sys

SRC = r'D:\用户目录\下载\新建文件夹 123\医生私下透露\体检查出这5种病，多数不用治——但要看清前提.html'
DST = r'D:\7tan\7tanAI\data\gzh_render\_extracted.html'

html = io.open(SRC, encoding='utf-8').read()
html_clean = re.sub(r'data:image/[a-z]+;base64,[A-Za-z0-9+/=]+', 'IMG_B64', html)
io.open(DST, 'w', encoding='utf-8').write(html_clean)
print('原始长度:', len(html), '-> 清理后:', len(html_clean))
