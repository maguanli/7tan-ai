# -*- coding: utf-8 -*-
"""删除旧 part01_v4.mp4（Python 宽字符安全删除）"""
import os
p = os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说', 'video', 'part01_v4.mp4')
if os.path.exists(p):
    os.remove(p)
    print("已删除 part01_v4.mp4")
else:
    print("part01_v4.mp4 不存在（可能之前已删除）")
# 也删掉旧的 ass（会重新生成）
for f in ['part01_v4.ass']:
    p2 = os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说', 'video', f)
    if os.path.exists(p2):
        os.remove(p2)
        print("已删除", f)
