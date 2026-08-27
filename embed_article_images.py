# -*- coding: utf-8 -*-
"""把文章HTML里的本地图片压缩后base64内嵌，变成单文件自包含HTML"""
import base64, re, io, os, sys
from PIL import Image

HTML = r"D:\7tan\7tanAI\data\gzh_render\医生私下透露：体检这5种病，根本不用治.html"
IMG_DIR = r"D:\7tan\7tanAI\downloads\article_images"

with open(HTML, "r", encoding="utf-8") as f:
    html = f.read()

pattern = re.compile(r'src="downloads/article_images/([^"]+)"')

def to_data_uri(m):
    name = m.group(1)
    path = os.path.join(IMG_DIR, name)
    if not os.path.exists(path):
        print("MISSING:", name)
        return m.group(0)
    img = Image.open(path).convert("RGB")
    w, h = img.size
    max_w = 1080
    if w > max_w:
        img = img.resize((max_w, int(h * max_w / w)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=82, optimize=True)
    data = base64.b64encode(buf.getvalue()).decode()
    print("OK %-28s %sx%s %dKB" % (name, img.size[0], img.size[1], len(buf.getvalue()) // 1024))
    return 'src="data:image/jpeg;base64,%s"' % data

html2, n = pattern.subn(to_data_uri, html)

with open(HTML, "w", encoding="utf-8") as f:
    f.write(html2)

print("replaced:", n)
print("new size: %.1f KB" % (os.path.getsize(HTML) / 1024))
