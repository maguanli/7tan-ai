# -*- coding: utf-8 -*-
"""《偏差》第3章 12图版竖屏视频制作脚本
流程：PIL生成片头/片尾卡 -> ffmpeg逐图渲染KenBurns片段 -> concat -> 合成氛围音 -> 合并输出
输出：720x1280@25fps  H.264+AAC  +faststart
"""
import os, subprocess, glob, textwrap

FFMPEG = "ffmpeg"
IMG_DIR = r"D:\7tan\7tanAI\镜像同事_小说\images\第3章"
TMP = r"D:\7tan\7tanAI\video_tmp"
CLIPS = os.path.join(TMP, "clips")
OUT = r"D:\7tan\7tanAI\镜像同事_小说\视频\偏差_第3章_梦游的备忘录_12图版.mp4"
os.makedirs(CLIPS, exist_ok=True)

W, H = 720, 1280
FPS = 25
DUR = 4          # 每张图秒数
FRAMES = DUR * FPS  # 100
FADE = 6         # 淡入淡出帧数 (~0.24s)

FONT_BD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT = r"C:\Windows\Fonts\msyh.ttc"

def run(cmd, timeout=120):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("CMD FAIL: " + " ".join(cmd[:6]) + "\n" + r.stderr[-2000:])
    return r

# ---------- 1. PIL 生成片头/片尾卡片 ----------
from PIL import Image, ImageDraw, ImageFont

def make_card(path, lines, big_size=72, sub_size=40, small_size=30):
    """lines: [(text, size, color), ...] 垂直居中排列"""
    img = Image.new("RGB", (W, H), (12, 14, 20))
    d = ImageDraw.Draw(img)
    # 深色氛围底：垂直渐变 + 底部微光
    for y in range(H):
        t = y / H
        r = int(12 + 14 * t); g = int(14 + 16 * t); b = int(20 + 26 * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    # 顶部细线 + 底部细线（装饰）
    d.rectangle([40, 90, W - 40, 94], fill=(180, 150, 90))
    d.rectangle([40, H - 96, W - 40, H - 92], fill=(180, 150, 90))
    # 文字
    total_h = sum(s for _, s, _ in lines)
    y = (H - total_h) // 2
    for txt, size, color in lines:
        f = ImageFont.truetype(FONT_BD if size >= 60 else FONT, size)
        # 居中
        bbox = d.textbbox((0, 0), txt, font=f)
        tw = bbox[2] - bbox[0]
        d.text(((W - tw) / 2, y - bbox[1]), txt, font=f, fill=color)
        y += size + 12
    img.save(path)

make_card(os.path.join(CLIPS, "card_head.png"), [
    ("悬疑连载 · 短篇小说", 30, (170, 170, 175)),
    ("偏  差", 100, (235, 225, 205)),
    ("第三章 · 梦游的备忘录", 44, (210, 180, 120)),
    ("备忘录，开始自己写记录了。", 30, (200, 200, 205)),
])
make_card(os.path.join(CLIPS, "card_tail.png"), [
    ("第三章 · 完", 72, (235, 225, 205)),
    ("偏差在加快 · 下一章见", 40, (210, 180, 120)),
    ("点赞 · 关注 · 追更", 30, (170, 170, 175)),
])

# ---------- 2. 逐图渲染片段 ----------
imgs = sorted(glob.glob(os.path.join(IMG_DIR, "*.png")))
assert len(imgs) == 12, f"expect 12 imgs, got {len(imgs)}"
seg_files = []

def zoom_expr(i):
    # 推拉交替：偶数为推(zoom+)，奇数为拉(zoom-)
    if i % 2 == 0:
        return "z='min(1.12,1+0.0012*on)'"
    return "z='max(1.0,1.12-0.0012*on)'"

for i, img in enumerate(imgs):
    out = os.path.join(CLIPS, f"seg_{i:02d}.mp4")
    vf = (
        f"scale=1440:2560:force_original_aspect_ratio=increase,"
        f"crop=1440:2560,"
        f"zoompan={zoom_expr(i)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={FRAMES}:s={W}x{H}:fps={FPS},"
        f"fade=t=in:st=0:d=0.24,fade=t=out:st={DUR-0.24}:d=0.24,"
        f"format=yuv420p"
    )
    run([FFMPEG, "-y", "-i", img, "-vf", vf, "-t", str(DUR),
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", out])
    seg_files.append(out)

# ---------- 3. 片头/片尾片段 ----------
head_out = os.path.join(CLIPS, "seg_head.mp4")
tail_out = os.path.join(CLIPS, "seg_tail.mp4")
run([FFMPEG, "-y", "-i", os.path.join(CLIPS, "card_head.png"),
     "-vf", f"scale=1440:2560,zoompan=z='min(1.05,1+0.0006*on)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=75:s={W}x{H}:fps={FPS},fade=t=in:st=0:d=0.3,fade=t=out:st=2.6:d=0.4,format=yuv420p",
     "-t", "3", "-c:v", "libx264", "-preset", "medium", "-crf", "20", head_out])
run([FFMPEG, "-y", "-i", os.path.join(CLIPS, "card_tail.png"),
     "-vf", f"scale=1440:2560,zoompan=z='min(1.05,1+0.0006*on)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=88:s={W}x{H}:fps={FPS},fade=t=in:st=0:d=0.4,fade=t=out:st=3.0:d=0.5,format=yuv420p",
     "-t", "3.5", "-c:v", "libx264", "-preset", "medium", "-crf", "20", tail_out])

# ---------- 4. concat ----------
all_segs = [head_out] + seg_files + [tail_out]
list_file = os.path.join(TMP, "concat.txt")
with open(list_file, "w", encoding="utf-8") as fp:
    for s in all_segs:
        fp.write(f"file '{s}'\n")
concat_out = os.path.join(TMP, "concat.mp4")
run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_file,
     "-c", "copy", concat_out], timeout=180)

# 总时长
probe = run([FFMPEG, "-i", concat_out, "-f", "null", "-"])
total_sec = 3 + 12 * DUR + 3.5  # 54.5

# ---------- 5. 合成氛围音（55Hz底 + 心跳脉动 + 棕色风噪） ----------
bg = os.path.join(TMP, "bg.m4a")
run([FFMPEG, "-y",
     "-f", "lavfi", "-i", f"sine=frequency=55:duration={total_sec}",
     "-f", "lavfi", "-i", f"anoisesrc=color=brown:duration={total_sec}:amplitude=0.4:seed=42",
     "-filter_complex",
     f"[0:a]tremolo=f=1.15:d=0.35,volume=0.16[low];"
     f"[1:a]lowpass=f=320,volume=0.22[noise];"
     f"[low][noise]amix=inputs=2:weights=1 1,"
     f"afade=t=in:st=0:d=1.2,afade=t=out:st={total_sec-2.5}:d=2.5[a]",
     "-map", "[a]", "-c:a", "aac", "-b:a", "128k", bg])

# ---------- 6. 合并输出 ----------
run([FFMPEG, "-y", "-i", concat_out, "-i", bg,
     "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
     "-shortest", "-movflags", "+faststart", OUT], timeout=180)

# ---------- 7. 抽帧质检 ----------
os.makedirs(os.path.join(TMP, "qc"), exist_ok=True)
qc_times = [0.5, 5, 25, 45, 53]  # 片头/第2张/中段/末段/片尾
for j, t in enumerate(qc_times):
    run([FFMPEG, "-y", "-ss", str(t), "-i", OUT, "-frames:v", "1",
         os.path.join(TMP, "qc", f"qc_{j}.png")])

size = os.path.getsize(OUT)
with open(os.path.join(TMP, "make_result.json"), "w", encoding="utf-8") as fp:
    import json
    json.dump({"out": OUT, "size_mb": round(size/1024/1024, 2),
               "duration": total_sec, "segments": len(all_segs),
               "qc_frames": len(qc_times)}, fp, ensure_ascii=False, indent=2)
print("ALL DONE")
