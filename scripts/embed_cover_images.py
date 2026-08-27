# -*- coding: utf-8 -*-
"""检查HTML中图片是否base64内嵌；若未内嵌则自动嵌入并覆盖保存"""
import re, os, base64, sys

P = r'D:\用户目录\下载\新建文件夹 123\医生私下透露\医生私下透露：体检这5种病，根本不用治.html'
IMG_DIR = r'D:\7tan\7tanAI\downloads\article_images'

html = open(P, encoding='utf-8').read()
print('文件大小:', os.path.getsize(P), 'bytes')
print('img标签数:', html.count('<img'))
print('base64内嵌数:', html.count('data:image'))

# 找出所有非内嵌的 src
srcs = re.findall(r'<img[^>]+src="([^"]+)"', html)
need_embed = [s for s in srcs if not s.startswith('data:image')]
print('外部引用图片数:', len(need_embed))
for s in need_embed:
    print('  -', s[:80])

if need_embed:
    # 按出现顺序映射到6张图（gzh_render按文中顺序渲染）
    files = sorted(f for f in os.listdir(IMG_DIR) if f.startswith('pexels-photo-'))
    print('可用图片:', files)
    idx = 0
    for s in need_embed:
        fname = os.path.basename(s.replace('\\', '/').split('?')[0])
        local = os.path.join(IMG_DIR, fname) if fname in files else os.path.join(IMG_DIR, files[min(idx, len(files)-1)])
        if not os.path.exists(local):
            print('!! 找不到本地图，跳过:', s[:60]); idx += 1; continue
        ext = 'jpeg' if local.lower().endswith(('.jpg', '.jpeg')) else 'png'
        b64 = base64.b64encode(open(local, 'rb').read()).decode()
        html = html.replace('src="%s"' % s, 'src="data:image/%s;base64,%s"' % (ext, b64), 1)
        print('已内嵌:', fname)
        idx += 1
    open(P, 'w', encoding='utf-8').write(html)
    print('已覆盖保存')

# 复检
html2 = open(P, encoding='utf-8').read()
srcs2 = re.findall(r'<img[^>]+src="([^"]+)"', html2)
print('---复检---')
print('最终大小:', os.path.getsize(P), 'bytes')
print('img总数:', len(srcs2), '| base64内嵌:', sum(1 for s in srcs2 if s.startswith('data:image')), '| 外部引用:', sum(1 for s in srcs2 if not s.startswith('data:image')))
