
"""
AI视频生成插件 - 整合 FFmpeg、MoviePy、edge-tts、ComfyUI
"""

import os
import sys
import subprocess
import json
import asyncio
from pathlib import Path

# === 配置 ===
BASE_DIR = Path("G:/AI_Video")
FFMPEG_EXE = BASE_DIR / "ffmpeg/ffmpeg-8.1.2-essentials_build/bin/ffmpeg.exe"
COMFYUI_DIR = BASE_DIR / "comfyui/ComfyUI"
OUTPUT_DIR = BASE_DIR / "output"
MODELS_DIR = BASE_DIR / "models"
SCRIPTS_DIR = BASE_DIR / "scripts"

# 确保输出目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


async def generate_tts_audio(text: str, voice: str = "zh-CN-XiaoxiaoNeural", output_filename: str = "tts_output.mp3") -> dict:
    """
    将文案转为配音音频（使用微软 Edge TTS，免费）
    
    参数:
        text: 要配音的文案文本
        voice: 配音音色，默认"zh-CN-XiaoxiaoNeural"(女声-晓晓)
               常用中文音色:
               - zh-CN-XiaoxiaoNeural (女-晓晓，活泼)
               - zh-CN-YunxiNeural (男-云希，磁性)
               - zh-CN-XiaoyiNeural (女-晓伊，温柔)
               - zh-CN-YunjianNeural (男-云健，沉稳)
               - zh-CN-YunxiaNeural (男-云夏，轻快)
        output_filename: 输出文件名
    """
    import edge_tts
    
    output_path = OUTPUT_DIR / output_filename
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))
    
    return {
        "success": True,
        "output_path": str(output_path),
        "voice": voice,
        "text_length": len(text),
        "file_size": output_path.stat().st_size if output_path.exists() else 0
    }


def compose_video(
    image_paths: str,
    audio_path: str = None,
    output_filename: str = "composed_video.mp4",
    duration_per_image: float = 3.0,
    subtitle_text: str = None,
    fps: int = 30,
    resolution: str = "1920x1080"
) -> dict:
    """
    将多张图片+配音+字幕合成视频
    
    参数:
        image_paths: 图片路径列表，JSON数组字符串如 '["img1.jpg","img2.jpg"]'
        audio_path: 配音/背景音乐路径（可选）
        output_filename: 输出视频文件名
        duration_per_image: 每张图片显示秒数
        subtitle_text: SRT格式字幕文本（可选）
        fps: 帧率
        resolution: 分辨率 WxH
    """
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
    import numpy as np
    
    images = json.loads(image_paths) if isinstance(image_paths, str) else image_paths
    output_path = OUTPUT_DIR / output_filename
    
    width, height = map(int, resolution.split('x'))
    
    clips = []
    for img_path in images:
        clip = ImageClip(img_path, duration=duration_per_image)
        clip = clip.resized((width, height))
        clips.append(clip)
    
    video = concatenate_videoclips(clips, method="compose")
    
    if audio_path and os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        # 如果音频比视频短，循环；比视频长，截断
        if audio.duration < video.duration:
            from moviepy import afx
            audio = audio.with_effects([afx.AudioLoop(duration=video.duration)])
        else:
            audio = audio.subclipped(0, video.duration)
        video = video.with_audio(audio)
    
    video.write_videofile(str(output_path), fps=fps, codec='libx264', audio_codec='aac')
    
    return {
        "success": True,
        "output_path": str(output_path),
        "duration": video.duration,
        "resolution": resolution,
        "image_count": len(images),
        "has_audio": audio_path is not None,
        "file_size": output_path.stat().st_size if output_path.exists() else 0
    }


def video_add_subtitle(
    video_path: str,
    subtitle_text: str,
    output_filename: str = "subtitled_video.mp4",
    font_size: int = 40,
    font_color: str = "white",
    bg_color: str = "black@0.5"
) -> dict:
    """
    给视频添加字幕（使用 FFmpeg）
    
    参数:
        video_path: 输入视频路径
        subtitle_text: SRT 格式字幕内容
        output_filename: 输出文件名
        font_size: 字体大小
        font_color: 字体颜色
        bg_color: 字幕背景色（如 black@0.5 半透明黑底）
    """
    output_path = OUTPUT_DIR / output_filename
    
    # 写入临时字幕文件
    srt_path = OUTPUT_DIR / "temp_subtitle.srt"
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(subtitle_text)
    
    cmd = [
        str(FFMPEG_EXE),
        "-i", str(video_path),
        "-vf", f"subtitles={srt_path}:force_style='FontSize={font_size},PrimaryColour=&H{font_color},BackColour=&H{bg_color}'",
        "-c:a", "copy",
        "-y",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    # 清理临时文件
    if srt_path.exists():
        srt_path.unlink()
    
    return {
        "success": output_path.exists(),
        "output_path": str(output_path),
        "stderr": result.stderr[-500:] if result.stderr else "",
        "file_size": output_path.stat().st_size if output_path.exists() else 0
    }


def comfyui_status() -> dict:
    """查看 ComfyUI 运行状态"""
    import httpx
    
    try:
        resp = httpx.get("http://127.0.0.1:8188/system_stats", timeout=5)
        stats = resp.json()
        return {
            "running": True,
            "version": stats.get("system", {}).get("comfyui_version", "unknown"),
            "device": stats.get("system", {}).get("device", "unknown"),
            "python_version": stats.get("system", {}).get("python_version", "unknown"),
            "ram_usage": f"{stats.get('system', {}).get('ram_total', 0) - stats.get('system', {}).get('ram_free', 0)}MB / {stats.get('system', {}).get('ram_total', 0)}MB",
            "installed_nodes": stats.get("system", {}).get("installed_nodes", 0)
        }
    except Exception as e:
        return {
            "running": False,
            "error": str(e),
            "tip": "ComfyUI 未启动，使用 comfyui_launch() 启动"
        }


def comfyui_launch(
    port: int = 8188,
    listen: bool = False,
    highvram: bool = False
) -> dict:
    """
    启动 ComfyUI 服务
    
    参数:
        port: 监听端口，默认 8188
        listen: 是否允许外部访问（0.0.0.0）
        highvram: 高显存模式（无GPU则忽略）
    """
    import subprocess
    
    cmd = [
        sys.executable,
        str(COMFYUI_DIR / "main.py"),
        "--port", str(port),
        "--cpu",
        "--output-directory", str(OUTPUT_DIR),
        "--input-directory", str(BASE_DIR / "input"),
    ]
    
    if listen:
        cmd.append("--listen")
    if highvram:
        cmd.append("--highvram")
    
    # 后台启动
    log_file = BASE_DIR / "comfyui.log"
    with open(log_file, 'w') as f:
        proc = subprocess.Popen(
            cmd,
            stdout=f,
            stderr=subprocess.STDOUT,
            cwd=str(COMFYUI_DIR)
        )
    
    return {
        "success": True,
        "pid": proc.pid,
        "port": port,
        "url": f"http://127.0.0.1:{port}",
        "log_file": str(log_file),
        "tip": "启动需要30-60秒，用 comfyui_status() 检查是否就绪"
    }


def comfyui_stop() -> dict:
    """停止 ComfyUI 服务"""
    import signal
    import subprocess
    
    # 查找并终止 ComfyUI 进程
    result = subprocess.run(
        ['taskkill', '/F', '/IM', 'python.exe', '/FI', 'WINDOWTITLE eq ComfyUI*'],
        capture_output=True, text=True
    )
    
    return {
        "success": True,
        "message": "已尝试终止 ComfyUI 进程",
        "detail": result.stdout.strip()
    }


def generate_srt_subtitles(
    text_segments: str,
    segment_duration: float = 3.0
) -> dict:
    """
    生成 SRT 格式字幕
    
    参数:
        text_segments: 字幕文本列表，JSON数组如 '["第一段文字","第二段文字"]'
        segment_duration: 每段字幕持续秒数
    """
    segments = json.loads(text_segments) if isinstance(text_segments, str) else text_segments
    
    srt_content = []
    for i, seg in enumerate(segments):
        start = i * segment_duration
        end = (i + 1) * segment_duration
        
        start_str = f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{int(start%60):02d},{int((start%1)*1000):03d}"
        end_str = f"{int(end//3600):02d}:{int((end%3600)//60):02d}:{int(end%60):02d},{int((end%1)*1000):03d}"
        
        srt_content.append(f"{i+1}\n{start_str} --> {end_str}\n{seg}\n")
    
    srt_text = "\n".join(srt_content)
    srt_path = OUTPUT_DIR / "generated_subtitles.srt"
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_text)
    
    return {
        "success": True,
        "srt_path": str(srt_path),
        "srt_content": srt_text,
        "segment_count": len(segments)
    }


def video_concat(
    video_paths: str,
    output_filename: str = "merged_video.mp4"
) -> dict:
    """
    合并多个视频文件
    
    参数:
        video_paths: 视频路径列表，JSON数组
        output_filename: 输出文件名
    """
    videos = json.loads(video_paths) if isinstance(video_paths, str) else video_paths
    output_path = OUTPUT_DIR / output_filename
    
    # 使用 FFmpeg concat
    concat_file = OUTPUT_DIR / "concat_list.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        for v in videos:
            f.write(f"file '{v}'\n")
    
    cmd = [
        str(FFMPEG_EXE),
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        "-y",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    if concat_file.exists():
        concat_file.unlink()
    
    return {
        "success": output_path.exists(),
        "output_path": str(output_path),
        "video_count": len(videos),
        "file_size": output_path.stat().st_size if output_path.exists() else 0
    }


def text_to_video_pipeline(
    script_text: str,
    voice: str = "zh-CN-XiaoxiaoNeural",
    output_name: str = "ai_video",
    subtitle_style: str = "bottom"
) -> dict:
    """
    一键文案转视频流水线：
    1. 生成配音
    2. 生成字幕
    3. 合成视频（需要先用 ComfyUI 生成关键帧图片）
    
    参数:
        script_text: 完整文案（用 \\n\\n 分段）
        voice: 配音音色
        output_name: 输出文件名前缀
        subtitle_style: 字幕样式 "bottom"/"center"
    """
    import asyncio
    
    paragraphs = [p.strip() for p in script_text.split('\n\n') if p.strip()]
    
    # Step 1: 生成配音
    full_text = ''.join(paragraphs)
    audio_result = asyncio.run(generate_tts_audio(full_text, voice, f"{output_name}_audio.mp3"))
    
    # Step 2: 生成字幕
    srt_result = generate_srt_subtitles(json.dumps(paragraphs), segment_duration=3.0)
    
    return {
        "success": True,
        "audio_path": audio_result["output_path"],
        "srt_path": srt_result["srt_path"],
        "paragraph_count": len(paragraphs),
        "next_step": f"用 ComfyUI 生成 {len(paragraphs)} 张关键帧图片，然后用 compose_video() 合成最终视频",
        "tip": "关键帧图片命名建议: frame_001.png, frame_002.png ..."
    }


# === 环境信息 ===
def get_environment_info() -> dict:
    """获取 AI 视频环境信息"""
    return {
        "base_dir": str(BASE_DIR),
        "ffmpeg": str(FFMPEG_EXE),
        "ffmpeg_exists": FFMPEG_EXE.exists(),
        "comfyui_dir": str(COMFYUI_DIR),
        "comfyui_exists": COMFYUI_DIR.exists(),
        "output_dir": str(OUTPUT_DIR),
        "models_dir": str(MODELS_DIR),
        "python_version": sys.version,
        "gpu_available": _check_gpu(),
        "disk_free_gb": round(
            __import__('shutil').disk_usage(str(BASE_DIR)).free / (1024**3), 1
        )
    }


def _check_gpu() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except:
        return False
