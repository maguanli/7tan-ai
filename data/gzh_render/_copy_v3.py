# -*- coding: utf-8 -*-
import shutil, os, sys
sys.stdout.reconfigure(encoding='utf-8')
src = r'D:\7tan\7tanAI\data\gzh_render\体检查出这5种病_v3.html'
dst = r'D:\用户目录\下载\新建文件夹 123\医生私下透露\体检查出这5种病，多数不用治——但要看清前提.html'
shutil.copy2(src, dst)
print('复制完成:', os.path.getsize(dst), 'bytes')
for f in sorted(os.listdir(os.path.dirname(dst))):
    print(' -', f)
