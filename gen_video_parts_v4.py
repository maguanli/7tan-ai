# -*- coding: utf-8 -*-
"""
《偏差》第一章 v4 视频分批渲染
修复：
1. 运镜改用 ffmpeg zoompan（平滑插值，消除 moviepy 逐帧 lambda 的抖动）
2. 字幕改用 ASS 字幕（libass 渲染，自动换行，MarginV 控制安全区，不再被遮）
3. 底部渐变条用 PIL 生成 PNG + overlay
用法: python gen_video_parts_v4.py [start] [end]
"""
import os, sys, subprocess, math

BASE = os.path.join(r"D:\7tan\7tanAI", "镜像同事_小说")
IMG_DIR = os.path.join(BASE, "images", "第1章")
AUD_DIR = os.path.join(BASE, "audio")
OUT_DIR = os.path.join(BASE, "video")
W, H = 720, 1280
FPS = 30

SEGS = [
    ("ch01_01.png", "seg01.mp3", "那个梦，我一点都记不起来了。", "zoom_in"),
    ("ch01_02.png", "seg02.mp3", "昨晚，我没说实话。", "pan_lr"),
    ("ch01_03.png", "seg03.mp3", "我的脚步，忽然顿住了。", "zoom_out"),
    ("ch01_04.png", "seg04.mp3", "那颗痣，本该在右耳。", "zoom_in"),
    ("ch01_05.png", "seg05.mp3", "那是一个右撇子的坐姿。", "pan_rl"),
    ("ch01_06.png", "seg06.mp3", "他全都不认得了。", "zoom_out"),
    ("ch01_07.png", "seg07.mp3", "只有我，笑不出来。", "pan_lr"),
    ("ch01_08.png", "seg08.mp3", "没有一样，用的是左手。", "zoom_in"),
    ("ch01_09.png", "seg09.mp3", "我不记得，自己什么时候写下它们。", "pan_up"),
    ("ch01_10.png", "seg10.mp3", "工牌上的照片，好像换了一张。", "zoom_in"),
    ("ch01_11.png", "seg11.mp3", "「1月3日：江辰。开始。」", "zoom_in"),
    ("ch01_12.png", "seg12.mp3", "老周，正在被替换。", "zoom_out"),
]


def ffprobe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=30)
    return float(r.stdout.strip())


def make_ass_text(text):
    """长句手动断行 + 转义"""
    text = text.replace(",", "，")  # ASS 英文逗号会截断字段
    if len(text) > 15 and "\\N" not in text:
        mid = len(text) // 2
        cut = None
        for sep in "，。、；：":
            idx = text.find(sep, mid - 6, mid + 6)
            if idx >= 0:
                cut = idx + 1
                break
        if cut is None:
            cut = mid
        text = text[:cut] + "\\N" + text[cut:]
    return text


def write_ass(path, text, dur):
    t0 = "0:00:00.00"
    t1 = f"0:00:{int(dur):02d}.{int((dur % 1) * 100):02d}"
    body = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,38,&H00FFFFFF,&H00FFFFFF,&H00101010,&H96000000,0,0,0,0,100,100,0,0,1,3,1,2,40,40,225,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,{t0},{t1},Default,,0,0,0,,{make_ass_text(text)}
"""
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(body)


def make_gradient(path):
    """底部渐变条 720x260：上透明 -> 下黑(alpha~200)"""
    try:
        import numpy as np
        from PIL import Image
        arr = np.zeros((260, W, 4), dtype=np.uint8)
        for i in range(260):
            a = int(205 * (i / 259) ** 1.3)
            arr[i, :, 3] = a
        Image.fromarray(arr, "RGBA").save(path)
        return True
    except Exception as e:
        print("PIL 生成渐变条失败:", e)
        return False


def motion_exprs(motion, n):
    """zoompan 表达式（不含逗号，避免破坏滤镜解析）"""
    z = x = y = None
    if motion == "zoom_in":
        z = f"1+0.13*on/{n}"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "zoom_out":
        z = f"1.13-0.13*on/{n}"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan_lr":
        z = "1.16"
        x = f"(iw-iw/zoom)*on/{n}"
        y = "(ih-ih/zoom)/2"
    elif motion == "pan_rl":
        z = "1.16"
        x = f"(iw-iw/zoom)*(1-on/{n})"
        y = "(ih-ih/zoom)/2"
    elif motion == "pan_up":
        z = "1.16"
        x = "(iw-iw/zoom)/2"
        y = f"(ih-ih/zoom)*(1-on/{n})"
    return z, x, y


def render_one(idx):
    img_name, aud_name, subtitle, motion = SEGS[idx]
    img_path = os.path.join(IMG_DIR, img_name)
    aud_path = os.path.join(AUD_DIR, aud_name)
    part = os.path.join(OUT_DIR, f"part{idx+1:02d}_v4.mp4")
    # 输入用绝对路径（Python subprocess 宽字符传参，ffmpeg 可处理中文绝对路径）
    # 输出/字幕/渐变用相对 ASCII 路径（cwd=OUT_DIR）
    rel_grad = "gradient_v4.png"
    rel_ass = f"part{idx+1:02d}_v4.ass"
    rel_part = f"part{idx+1:02d}_v4.mp4"
    if os.path.exists(part) and os.path.getsize(part) > 100000:
        print(f"part{idx+1:02d}: 已存在，跳过", flush=True)
        return "skip"
    dur = ffprobe_duration(aud_path)
    n = max(int(round(dur * FPS)) + 10, 30)
    z, x, y = motion_exprs(motion, n)

    grad = os.path.join(OUT_DIR, "gradient_v4.png")
    if not os.path.exists(grad):
        make_gradient(grad)

    ass_name = f"part{idx+1:02d}_v4.ass"
    ass_path = os.path.join(OUT_DIR, ass_name)
    write_ass(ass_path, subtitle, dur)

    fc = (
        f"[0:v]scale=2880:5120:flags=lanczos,"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={W}x{H}:fps={FPS},format=yuv420p[bg];"
        f"[bg][1:v]overlay=0:1010[bg2];"
        f"[bg2]subtitles={rel_ass}[v];"
        f"[2:a]aformat=sample_rates=44100:channel_layouts=stereo[a]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", img_path,
        "-i", rel_grad,
        "-i", aud_path,
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        rel_part,
    ]
    print(f"part{idx+1:02d}: 渲染中 (dur={dur:.1f}s n={n}) ...", flush=True)
    r = subprocess.run(cmd, cwd=OUT_DIR, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=240)
    if r.returncode != 0:
        print(f"part{idx+1:02d}: FAIL\n{r.stderr[-800:]}", flush=True)
        return "fail"
    print(f"part{idx+1:02d}: OK ({os.path.getsize(part)//1024}KB)", flush=True)
    return "ok"


def render_range(s, e):
    done = skip = fail = 0
    for i in range(s - 1, min(e, len(SEGS))):
        r = render_one(i)
        if r == "ok":
            done += 1
        elif r == "skip":
            skip += 1
        else:
            fail += 1
    print(f"完成: 新渲染 {done}, 跳过 {skip}, 失败 {fail}", flush=True)


if __name__ == "__main__":
    s = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    e = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    render_range(s, e)
