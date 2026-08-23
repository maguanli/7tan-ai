# -*- coding: utf-8 -*-
"""相邻帧差异分析：验证运镜平滑（无抖动）"""
import os
import numpy as np
from PIL import Image

f1 = r'D:\7tan\7tanAI\frame_a1.png'
f2 = r'D:\7tan\7tanAI\frame_a2.png'

a = np.asarray(Image.open(f1).convert('L'), dtype=np.float32)
b = np.asarray(Image.open(f2).convert('L'), dtype=np.float32)
diff = np.abs(a - b).mean()
print(f"相邻帧(1/30秒间隔)平均像素差: {diff:.3f}")
print("判定: " + ("平滑（正常运镜位移）" if diff < 8 else "异常（可能存在抖动/突变）"))
