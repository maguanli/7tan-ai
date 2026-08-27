# -*- coding: utf-8 -*-
"""将修订版HTML中的6张图片转为base64内嵌，删除旧版HTML，列出最终文件"""
import base64, re, os, glob

folder = r'D:\用户目录\下载\新建文件夹 123\医生私下透露'
html_path = os.path.join(folder, '体检查出这5种病，多数不用治——但要看清前提.html')

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

img_dir = r'D:\7tan\7tanAI\downloads\article_images'
count = 0
pattern = r'src="(D:/7tan/7tanAI/downloads/article_images/[^"]+)"'
for m in re.findall(pattern, html):
    local = m.replace('/', '\\')
    if os.path.exists(local):
        ext = os.path.splitext(local)[1].lower().lstrip('.')
        mime = 'image/png' if ext == 'png' else 'image/jpeg'
        b64 = base64.b64encode(open(local, 'rb').read()).decode()
        html = html.replace('src="' + m + '"', 'src="data:' + mime + ';base64,' + b64 + '"')
        count += 1

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

total = len(re.findall(r'<img', html))
embedded = len(re.findall(r'src="data:image', html))
external = total - embedded
size_kb = os.path.getsize(html_path) // 1024
print('img_total=%d embedded=%d external=%d size=%dKB' % (total, embedded, external, size_kb))

for old in glob.glob(os.path.join(folder, '*医生私下透露*.html')):
    os.remove(old)
    print('removed_old:', os.path.basename(old))

print('--- final files ---')
for f in sorted(os.listdir(folder)):
    print('%6d KB  %s' % (os.path.getsize(os.path.join(folder, f)) // 1024, f))
