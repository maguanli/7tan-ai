# -*- coding: utf-8 -*-
"""检查视频文件状态与编码信息"""
import os, subprocess, sys

video_dir = os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说', 'video')
base = os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说')

print("=== video 目录文件 ===")
for f in os.listdir(video_dir):
    full = os.path.join(video_dir, f)
    print(f"{os.path.getsize(full):>12,}  {f}")

print("\n=== ffprobe 检查所有 mp4 ===")
candidates = [f for f in os.listdir(video_dir) if f.lower().endswith('.mp4')]
for f in candidates:
    full = os.path.join(video_dir, f)
    try:
        r = subprocess.run(
            [r'D:\ffmpeg\bin\ffprobe.exe', '-v', 'error', '-show_entries',
             'format=duration,size,format_name:stream=codec_name,codec_type,width,height,r_frame_rate',
             '-of', 'json', full],
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        print(f"\n--- {f} ---")
        print((r.stdout or r.stderr)[:1200])
    except Exception as e:
        print(f"--- {f} 检查异常: {e}")

print("\n=== 查找分段/parts 目录 ===")
for d in os.listdir(base):
    dp = os.path.join(base, d)
    if os.path.isdir(dp) and ('part' in d.lower() or 'seg' in d.lower() or 'tmp' in d.lower()):
        print(f"[目录] {dp}")
        fs = sorted(os.listdir(dp))
        for f in fs[:30]:
            print(f"   {os.path.getsize(os.path.join(dp, f)):>12,}  {f}")

print("\n=== 查找生成脚本 ===")
for d in os.listdir(base):
    dp = os.path.join(base, d)
    if os.path.isdir(dp):
        for f in os.listdir(dp):
            if f.endswith('.py') and ('video' in f.lower() or 'gen' in f.lower() or 'concat' in f.lower()):
                print(f"{dp}\\{f}")
