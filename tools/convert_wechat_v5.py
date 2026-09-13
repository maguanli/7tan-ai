# -*- coding: utf-8 -*-
"""v4 精美版 -> 公众号粘贴兼容版 v5
1. base64 图片按 MD5 映射为 https://www.7tan.com/article/xxx.jpg 外链
2. linear-gradient 渐变背景 -> 纯色 background-color（微信编辑器不认渐变）
3. 去除 box-shadow / transform（微信编辑器会剥离）
"""
import re, base64, hashlib, os

SRC = r"D:\7tan\7tanAI\downloads\wechat_article\工资涨了3000_存款还是0_精美版_v4.html"
DST = r"D:\7tan\7tanAI\downloads\wechat_article\工资涨了3000_存款还是0_公众号兼容版.html"
IMG_DIR = r"D:\7tan\7tanAI\downloads\wechat_article"
BASE = "https://www.7tan.com/article/"

# 1. 本地图 md5 -> 文件名
def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

name_by_md5 = {}
for fn in os.listdir(IMG_DIR):
    if fn.lower().endswith(".jpg"):
        name_by_md5[md5_file(os.path.join(IMG_DIR, fn))] = fn

html = open(SRC, "r", encoding="utf-8").read()

# 2. 替换 base64 图片
def repl_img(m):
    b64 = m.group(1)
    try:
        raw = base64.b64decode(b64)
        md5 = hashlib.md5(raw).hexdigest()
    except Exception:
        return m.group(0)
    fn = name_by_md5.get(md5)
    if fn:
        return '<img src="%s%s" style="max-width:100%%;height:auto;border-radius:8px;display:block;margin:0 auto;" />' % (BASE, fn)
    return m.group(0)

html, n_img = re.subn(r'<img src="data:image/jpeg;base64,([^"]+)"[^>]*/?>', repl_img, html)

# 3. 样式降级
def no_grad(m):
    return "background-color:#1e3a5f"

html, n_grad = re.subn(r'background:\s*linear-gradient\([^)]*\)', no_grad, html)
html, n_shadow = re.subn(r'box-shadow:[^;"\']*;?', "", html)
html, n_transform = re.subn(r'transform:[^;"\']*;?', "", html)

open(DST, "w", encoding="utf-8").write(html)

# 4. 统计
n_b64_left = len(re.findall(r'data:image/jpeg;base64,', html))
n_url = len(re.findall(r'<img src="https://www\.7tan\.com/article/', html))
print("IMG_REPLACED=%d GRAD_REMOVED=%d SHADOW_REMOVED=%d TRANSFORM_REMOVED=%d" % (n_img, n_grad, n_shadow, n_transform))
print("IMG_URL=%d BASE64_LEFT=%d" % (n_url, n_b64_left))
print("DST=%s" % DST)
