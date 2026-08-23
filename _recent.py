# -*- coding: utf-8 -*-
import os, time
now = time.time()
hits = []
for root, dirs, files in os.walk(r'D:\7tan\7tanAI'):
    dirs[:] = [d for d in dirs if d not in ('node_modules', '.venv', '.git', 'build', 'dist', '__pycache__')]
    for f in files:
        if f.lower().endswith('.png'):
            p = os.path.join(root, f)
            st = os.stat(p)
            age = now - st.st_mtime
            if age < 1800:  # 最近30分钟内
                hits.append((st.st_mtime, st.st_size//1024, p))
hits.sort(reverse=True)
for m, kb, p in hits[:30]:
    print('%s | %dKB | %s' % (time.strftime('%H:%M:%S', time.localtime(m)), kb, p))
print('total recent:', len(hits))
