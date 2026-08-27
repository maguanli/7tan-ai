# -*- coding: utf-8 -*-
"""同步模板文档到构建产物目录"""
import shutil, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = r"D:\7tan\7tanAI\templates\7Tan使用说明书.md"
DST_DIR = r"D:\7tan\7tanAI\dist\7tan-editor"
DST = os.path.join(DST_DIR, "7Tan使用说明书.md")
shutil.copy(SRC, DST)
print("已复制:", SRC, "->", DST)
print("大小:", os.path.getsize(DST))
