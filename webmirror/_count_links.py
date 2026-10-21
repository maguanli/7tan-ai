# -*- coding: utf-8 -*-
import os, re, collections, random

TASK = r"D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb"
ROOT = os.path.join(TASK, "youbian.293.net")

files = [f for f in os.listdir(ROOT) if f.endswith(".html")]
print("html 文件数:", len(files))

random.seed(1)
sample = random.sample(files, min(6, len(files)))
pat = re.compile(r'href\s*=\s*["\']([^"\']*id_[A-Za-z0-9]+\.html)[^"\']*["\']')

total_links = 0
case_variants = collections.Counter()
examples = []
for fn in sample:
    fp = os.path.join(ROOT, fn)
    try:
        with open(fp, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()
    except Exception:
        continue
    links = pat.findall(html)
    for l in links:
        total_links += 1
        m = re.search(r'id_([A-Za-z0-9]+)\.html', l)
        if m:
            s = m.group(1)
            low = s.lower()
            if s != low:
                case_variants["有大小写混合"] += 1
            else:
                case_variants["全小写"] += 1
    if links and len(examples) < 3:
        examples.append((fn, links[:6]))

print("\n抽样 %d 个页面，共提取 id_ 链接 %d 条" % (len(sample), total_links))
for k, v in case_variants.items():
    print("   ", k, v)

print("\n链接样例:")
for fn, ls in examples:
    print("  来自:", fn)
    for l in ls:
        print("        ", l)
