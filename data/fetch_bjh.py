# -*- coding: utf-8 -*-
"""抓取百家号文章正文并解析为纯文本"""
import re, html, io, sys, urllib.request, ssl

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = "https://baijiahao.baidu.com/s?id=1875475249087906432"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://www.baidu.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(url, headers=headers)
raw = urllib.request.urlopen(req, timeout=30, context=ctx).read().decode("utf-8", errors="ignore")
open("data/bjh_hepatitis.html", "w", encoding="utf-8").write(raw)
print("HTML大小:", len(raw))

# 标题
tm = re.search(r"<title>(.*?)</title>", raw, re.S)
print("TITLE:", html.unescape(tm.group(1)).strip() if tm else "无")

# 正文容器尝试多个模式
body = None
for pat in [
    r'<div[^>]*class="[^"]*article-content[^"]*"[^>]*>(.*?)</div>\s*</div>',
    r'id="article-content"[^>]*>(.*?)</div>',
    r'class="index-module_articleWrap[^"]*"[^>]*>(.*?)</div>\s*</div>',
    r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)<div[^>]*class="[^"]*comment',
]:
    m = re.search(pat, raw, re.S)
    if m and len(m.group(1)) > 500:
        body = m.group(1)
        break

if not body:
    print("未找到正文容器，尝试全文清洗…")
    # 去掉 head 和脚本后取 body 文本
    m = re.search(r"<body.*?>(.*)</body>", raw, re.S)
    body = m.group(1) if m else raw

body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
body = re.sub(r"<style.*?</style>", "", body, flags=re.S)
body = re.sub(r"<br\s*/?>", "\n", body)
body = re.sub(r"</p>", "\n", body)
body = re.sub(r"</h[1-6]>", "\n", body)
text = re.sub(r"<[^>]+>", "", body)
text = html.unescape(text)
lines = [l.strip() for l in text.split("\n") if l.strip()]
out = "\n".join(lines)
open("data/bjh_hepatitis_text.txt", "w", encoding="utf-8").write(out)
print("=== 正文纯文本（前6000字）===")
print(out[:6000])
print("=== 结束 ===")
print("总字数:", len(out))
