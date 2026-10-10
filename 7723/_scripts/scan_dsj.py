# -*- coding: utf-8 -*-
import io, json
wf = r"D:\7tan\7tanAI\config\sensitive_words.txt"
uf = r"D:\7tan\7tanAI\7723\7723大事记_UBB.txt"
words = [w.strip() for w in io.open(wf, encoding='utf-8').read().splitlines()
         if w.strip() and not w.strip().startswith('#')]
text = io.open(uf, encoding='utf-8').read()
print("词库(%d):" % len(words), words)
hits = {}
for w in words:
    c = text.count(w)
    if c:
        hits[w] = c
print("命中:", json.dumps(hits, ensure_ascii=False))
print("正文长度(字符):", len(text))
for w in hits:
    i = text.find(w)
    print("  --", w, "→ …", text[max(0, i-40):i+40].replace("\n", " "), "…")
