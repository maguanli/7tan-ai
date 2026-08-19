# -*- coding: utf-8 -*-
"""分析第三章视频开头2秒：提取前几帧保存，供视觉诊断"""
import cv2, os

video = r"D:\7tan\7tanAI\downloads\fanqie\video\chapter3_manhua_seedream.mp4"
outdir = r"D:\7tan\7tanAI\downloads\fanqie\video\open_frames"
os.makedirs(outdir, exist_ok=True)

print("视频存在:", os.path.exists(video))
if not os.path.exists(video):
    raise SystemExit("视频不存在")

cap = cv2.VideoCapture(video)
fps = cap.get(cv2.CAP_PROP_FPS)
frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"fps={fps:.2f} frames={frames} 分辨率={w}x{h} 时长={frames/fps:.1f}s")

# 提取开头 0.1s / 0.5s / 1.0s / 1.5s / 2.0s / 3.0s / 5.0s 的帧
times = [0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
for t in times:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, frame = cap.read()
    if ok:
        fname = os.path.join(outdir, f"t{t:04.1f}s.png")
        cv2.imwrite(fname, frame)
        print(f"已保存 {fname}")

cap.release()
print("完成")
