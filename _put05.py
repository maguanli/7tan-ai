# -*- coding: utf-8 -*-
import os, shutil
src = r'D:\7tan\7tanAI\novel_img\ch01_05.png'
dst = r'D:\7tan\7tanAI\镜像同事_小说\images\ch01_05.png'
shutil.copy2(src, dst)
print('exists:', os.path.exists(dst), os.path.getsize(dst)//1024, 'KB')
