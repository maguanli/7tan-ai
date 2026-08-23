# -*- coding: utf-8 -*-
"""单独检查最终 v3 拼接视频 + 找生成脚本"""
import os, subprocess, glob

video_dir = os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说', 'video')
base = os.path.join(r'D:\7tan\7tanAI', '镜像同事_小说')

# 找 v3 最终文件
final = None
for f in os.listdir(video_dir):
    if 'v3' in f and f.endswith('.mp4') and 'part' not in f:
        final = os.path.join(video_dir, f)
        break
print("最终文件:", final, os.path.getsize(final) if final else None)

if final:
    # ffprobe 详细信息
    r = subprocess.run(
        [r'D:\ffmpeg\bin\ffprobe.exe', '-v', 'error',
         '-show_entries', 'format=duration,size,format_name:stream=codec_name,codec_type,width,height,r_frame_rate,start_time,duration_ts,time_base',
         '-of', 'json', final],
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    print("ffprobe:", r.stdout[:2000] if r.stdout else r.stderr[:500])

    # 尝试解码前 5 帧验证可播放性
    r2 = subprocess.run(
        [r'D:\ffmpeg\bin\ffmpeg.exe', '-v', 'error', '-i', final, '-frames:v', '5',
         '-f', 'null', '-'],
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    print("解码前5帧:", "OK 无错误" if r2.returncode == 0 else f"FAIL: {r2.stderr[:800]}")

# 列出所有 py 脚本
print("\n=== 镜像同事_小说 目录下 py 脚本 ===")
for f in os.listdir(base):
    if f.endswith('.py'):
        print(f, os.path.getsize(os.path.join(base, f)))

# 查找子目录中的 py
print("\n=== 所有子目录 py（video/gen 相关）===")
for root, dirs, files in os.walk(base):
    if '__pycache__' in root or '.git' in root:
        continue
    for f in files:
        if f.endswith('.py') and any(k in f.lower() for k in ('video', 'gen', 'concat', 'render', 'ken')):
            print(os.path.join(root, f))
