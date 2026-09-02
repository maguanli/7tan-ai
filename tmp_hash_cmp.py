# -*- coding: utf-8 -*-
import hashlib, glob, os, time, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
cur = 'src/agent/world_model.py'
cur_h = hashlib.md5(open(cur, 'rb').read()).hexdigest()[:12]
print('当前文件:', cur, os.path.getsize(cur), 'B, md5=' + cur_h)
print('--- 各备份 vs 当前 ---')
for f in sorted(glob.glob('src/agent/world_model.py.bak*')):
    h = hashlib.md5(open(f, 'rb').read()).hexdigest()[:12]
    same = '== 与当前完全一致' if h == cur_h else '!= 与当前不同'
    mt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(f)))
    print('%-42s %6d B  md5=%s  %s  %s' % (os.path.basename(f), os.path.getsize(f), h, mt, same))
