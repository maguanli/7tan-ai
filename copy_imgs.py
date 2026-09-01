# -*- coding: utf-8 -*-
import shutil, glob, os

dst = r'data/gzh_render/塞班游戏站捡漏'
os.makedirs(dst, exist_ok=True)
for f in glob.glob(r'downloads/article_saiban/*.jpg'):
    shutil.copy(f, os.path.join(dst, os.path.basename(f)))
print('OK:', sorted(os.listdir(dst)))
