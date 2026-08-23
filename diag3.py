# -*- coding: utf-8 -*-
"""深度诊断：列出 D:\7tan\7tanAI 下所有目录的真实名称和 images 内容，写入 UTF-8 日志"""
import os

log = []

def log_line(s):
    log.append(s)

root = r'D:\7tan\7tanAI'
log_line("=== D:\\7tan\\7tanAI 顶层目录 ===")
for e in os.scandir(root):
    if e.is_dir():
        log_line(f"  DIR name={e.name!r}")

log_line("")
log_line("=== 各子目录下 images/video 情况 ===")
for e in os.scandir(root):
    if e.is_dir():
        d = e.path
        # 找含中文的目录
        if any(ord(c) > 127 for c in e.name):
            log_line(f"[目录] {e.name!r} -> {d!r}")
            for sub in os.listdir(d):
                subp = os.path.join(d, sub)
                if os.path.isdir(subp):
                    items = os.listdir(subp)
                    log_line(f"   子目录 {sub!r}: {len(items)} 项 -> {items[:15]!r}")

log_line("")
log_line("=== video 目录 mp4 ===")
for e in os.scandir(root):
    if e.is_dir() and 'video' in e.name.lower():
        for f in sorted(os.listdir(e.path)):
            log_line(f"  {f!r} {os.path.getsize(os.path.join(e.path, f))}")

log_line("")
log_line("=== 尝试多种中文名拼法 ===")
import unicodedata
candidates = ['镜像同事_小说', '镜像同事_小说'.replace('事', '事')]
for cand in candidates:
    p = os.path.join(root, cand)
    log_line(f"  拼法 {cand!r} (NFC={unicodedata.is_normalized('NFC', cand)} NFD={unicodedata.is_normalized('NFD', cand)}): exists={os.path.exists(p)}")

# 用 glob 找所有含"小说"的路径
log_line("")
log_line("=== glob 搜索含'小说'的目录 ===")
import glob
for p in glob.glob(os.path.join(root, '*小说*')):
    log_line(f"  {p!r} exists={os.path.exists(p)}")

with open(os.path.join(root, 'diag_log.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(log))
print("已写入 diag_log.txt，共", len(log), "行")
