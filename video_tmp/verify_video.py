# -*- coding: utf-8 -*-
"""验证视频元数据 + 抽帧质检"""
import subprocess, json, os

OUT = r"D:\7tan\7tanAI\镜像同事_小说\视频\偏差_第3章_梦游的备忘录_12图版.mp4"
TMP = r"D:\7tan\7tanAI\video_tmp"

def run(cmd, timeout=60):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-1500:])
    return r

# 1. 元数据
probe = run(["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", OUT])
info = json.loads(probe.stdout)
meta = {"duration": float(info["format"]["duration"]),
        "size_mb": round(os.path.getsize(OUT)/1024/1024, 2)}
for s in info["streams"]:
    if s["codec_type"] == "video":
        meta["video"] = {"codec": s["codec_name"], "w": s["width"], "h": s["height"],
                         "fps": s.get("r_frame_rate"), "pix_fmt": s.get("pix_fmt")}
    else:
        meta["audio"] = {"codec": s["codec_name"], "sample_rate": s.get("sample_rate"),
                         "channels": s.get("channels")}

# 2. 检查快进播放友好
meta["faststart"] = "moov" in open(OUT, "rb").read(400000).decode("latin1")[:200000] if os.path.getsize(OUT) > 0 else False

# 3. 抽帧（多时间点）
qc = os.path.join(TMP, "qc2")
os.makedirs(qc, exist_ok=True)
times = [0.8, 4, 12, 20, 28, 36, 44, 52]
frames = []
for j, t in enumerate(times):
    p = os.path.join(qc, f"f{j}.png")
    run(["ffmpeg", "-y", "-ss", str(t), "-i", OUT, "-frames:v", "1", p])
    frames.append(p)

meta["qc_frames"] = frames
with open(os.path.join(TMP, "verify_result.json"), "w", encoding="utf-8") as fp:
    json.dump(meta, fp, ensure_ascii=False, indent=2)
print("VERIFY DONE")
