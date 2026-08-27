# -*- coding: utf-8 -*-
"""检查5个疑似临时文件：头部内容 + 敏感词扫描（只读）"""
import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FILES = [
    r"D:\7tan\7tanAI\tools\_tmp_check_apppy.py",
    r"D:\7tan\7tanAI\tools\_tmp_check_apppy2.py",
    r"D:\7tan\7tanAI\tools\_tmp_check_procs.py",
    r"D:\7tan\7tanAI\tools\_verify_click_feedback.py",
    r"D:\7tan\7tanAI\tools\gzh_publish\ocr_verify_dialog.py",
]
SENS = [("img.7tan.cn", r"img\.7tan\.cn"), ("真实key", r"sk-cPHNv"), ("admin", r"username:\s*admin")]

for f in FILES:
    print("=" * 70)
    print("文件:", os.path.basename(f), "| 大小:", os.path.getsize(f), "B")
    with open(f, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    # 头部 12 行
    lines = text.splitlines()
    print("--- 头部 12 行 ---")
    for ln in lines[:12]:
        print("   ", ln[:100])
    # 敏感词
    hits = []
    for label, pat in SENS:
        ms = re.findall(pat, text)
        if ms:
            hits.append(f"{label}:{ms[:2]}")
    print("敏感词:", hits if hits else "无")
