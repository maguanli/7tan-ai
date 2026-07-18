
"""
AI视频生成工具集
- Edge TTS 免费配音（中文多音色）
- MoviePy 视频剪辑合成
- FFmpeg 转码/加字幕
- ComfyUI API 调用（可选）
"""

import subprocess
import os
import asyncio
import json
from pathlib import Path

# === 配置 ===
COMFYUI_PATH = r"G:\AI_Tools\ComfyUI"
FFMPEG_PATH = r"G:\AI_Tools\FFmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"
OUTPUT_DIR = r"G:\AI_Video\projects"


def tts_generate(text: str, voice: str = "zh-CN-XiaoxiaoNeural", output: str = None, rate: str = "+0%") -> dict:
    """
    使用 Edge TTS 生成配音（免费，中文多音色）
    
    常用中文音色:
    - zh-CN-XiaoxiaoNeural (女，温柔)
    - zh-CN-YunxiNeural (男，沉稳)
    - zh-CN-XiaoyiNeural (女，活泼)
    - zh-CN-YunjianNeural (男，老成)
    
    参数:
    - text: 要配音的文本
    - voice: 音色名称
    - output: 输出mp3路径（默认自动生成）
    - rate: 语速，如 "+20%" 或 "-10%"
    
    返回: {"success": bool, "path": str, "size": int}
    """
    if output is None:
        import tempfile, time
        output = os.path.join(OUTPUT_DIR, f"tts_{int(time.time())}.mp3")
    
    os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
    
    try:
        result = subprocess.run(
            ["edge-tts", "--voice", voice, "--text", text, "--rate", rate, "--write-media", output],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and os.path.exists(output):
            size = os.path.getsize(output)
            return {"success": True, "path": output, "size": size, "text_length": len(text)}
        return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


def video_from_images(image_dir: str, audio_path: str, output: str = None, 
                      fps: int = 2, duration_per_image: float = None) -> dict:
    """
    将图片序列+配音合成视频
    
    参数:
    - image_dir: 图片目录（按文件名排序）
    - audio_path: 配音mp3路径
    - output: 输出mp4路径
    - fps: 帧率
    - duration_per_image: 每张图时长（秒），不指定则按音频时长均分
    
    返回: {"success": bool, "path": str}
    """
    from moviepy import ImageSequenceClip, AudioFileClip
    import time
    
    if output is None:
        output = os.path.join(OUTPUT_DIR, f"video_{int(time.time())}.mp4")
    
    os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
    
    try:
        # 收集图片
        images = sorted([
            os.path.join(image_dir, f) for f in os.listdir(image_dir)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return {"success": False, "error": f"在 {image_dir} 中没找到图片"}
        
        # 加载音频获取时长
        audio = AudioFileClip(audio_path)
        
        if duration_per_image:
            durations = [duration_per_image] * len(images)
        else:
            dur = audio.duration / len(images)
            durations = [dur] * len(images)
        
        # 合成
        clip = ImageSequenceClip(images, durations=durations)
        clip = clip.with_audio(audio)
        clip.write_videofile(output, fps=fps, codec='libx264', audio_codec='aac')
        
        clip.close()
        audio.close()
        
        return {"success": True, "path": output, "image_count": len(images), "duration": audio.duration}
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_subtitle(video_path: str, srt_path: str, output: str = None) -> dict:
    """
    给视频添加SRT字幕（用FFmpeg）
    
    参数:
    - video_path: 视频路径
    - srt_path: SRT字幕文件路径
    - output: 输出路径
    
    返回: {"success": bool, "path": str}
    """
    if output is None:
        base, ext = os.path.splitext(video_path)
        output = f"{base}_subbed{ext}"
    
    try:
        # FFmpeg subtitles filter
        srt_abs = os.path.abspath(srt_path).replace('\\', '/').replace(':', '\\\\:')
        result = subprocess.run([
            FFMPEG_PATH, "-i", video_path, "-vf", f"subtitles='{srt_abs}'",
            "-c:a", "copy", "-y", output
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(output):
            return {"success": True, "path": output}
        return {"success": False, "error": result.stderr[-500:]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def video_concat(video_list: list, output: str = None) -> dict:
    """
    拼接多个视频（用FFmpeg concat）
    
    参数:
    - video_list: 视频路径列表
    - output: 输出路径
    
    返回: {"success": bool, "path": str}
    """
    import tempfile, time
    
    if output is None:
        output = os.path.join(OUTPUT_DIR, f"concat_{int(time.time())}.mp4")
    
    os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
    
    try:
        # 写concat列表文件
        list_file = os.path.join(tempfile.gettempdir(), f"concat_list_{int(time.time())}.txt")
        with open(list_file, 'w', encoding='utf-8') as f:
            for v in video_list:
                f.write(f"file '{os.path.abspath(v).replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n")
        
        result = subprocess.run([
            FFMPEG_PATH, "-f", "concat", "-safe", "0", "-i", list_file,
            "-c", "copy", "-y", output
        ], capture_output=True, text=True, timeout=300)
        
        os.remove(list_file) if os.path.exists(list_file) else None
        
        if result.returncode == 0:
            return {"success": True, "path": output, "count": len(video_list)}
        return {"success": False, "error": result.stderr[-500:]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def video_info(video_path: str) -> dict:
    """
    获取视频信息（时长/分辨率/编码等）
    """
    try:
        result = subprocess.run([
            FFMPEG_PATH, "-i", video_path
        ], capture_output=True, text=True, timeout=30)
        # ffmpeg info goes to stderr
        info = result.stderr
        return {"success": True, "info": info}
    except Exception as e:
        return {"success": False, "error": str(e)}


def text_to_srt(text: str, duration: float, output: str = None) -> dict:
    """
    将文本转为SRT字幕（单条或每条一行自动分段）
    
    参数:
    - text: 文本（每行一条字幕）
    - duration: 总时长（秒）
    - output: SRT输出路径
    
    返回: {"success": bool, "path": str}
    """
    import time
    
    if output is None:
        output = os.path.join(OUTPUT_DIR, f"subtitle_{int(time.time())}.srt")
    
    os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
    
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    dur_per_line = duration / len(lines)
    
    with open(output, 'w', encoding='utf-8') as f:
        for i, line in enumerate(lines):
            start = i * dur_per_line
            end = start + dur_per_line
            
            def fmt(t):
                h = int(t // 3600)
                m = int((t % 3600) // 60)
                s = int(t % 60)
                ms = int((t % 1) * 1000)
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            
            f.write(f"{i+1}\n")
            f.write(f"{fmt(start)} --> {fmt(end)}\n")
            f.write(f"{line}\n\n")
    
    return {"success": True, "path": output, "lines": len(lines)}


def comfyui_generate(prompt: str, workflow_type: str = "txt2img", 
                     negative_prompt: str = "", steps: int = 20,
                     width: int = 512, height: int = 512) -> dict:
    """
    调用 ComfyUI API 生成图片（需先启动 ComfyUI 服务）
    
    启动ComfyUI: cd G:\AI_Tools\ComfyUI && python main.py --cpu
    
    参数:
    - prompt: 正向提示词
    - workflow_type: txt2img / img2img
    - negative_prompt: 负向提示词
    - steps: 采样步数
    - width/height: 图片尺寸
    """
    import requests
    import uuid
    
    comfy_url = "http://127.0.0.1:8188"
    
    # 简单文生图workflow
    workflow = {
        "3": {"class_type": "KSampler", "inputs": {
            "seed": 42, "steps": steps, "cfg": 7.0,
            "sampler_name": "euler", "scheduler": "normal",
            "denoise": 1.0,
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0]
        }},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_prompt, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "ai_video", "images": ["8", 0]}},
    }
    
    try:
        client_id = str(uuid.uuid4())
        resp = requests.post(f"{comfy_url}/prompt", json={
            "prompt": workflow, "client_id": client_id
        }, timeout=300)
        
        if resp.status_code == 200:
            prompt_id = resp.json().get("prompt_id")
            return {"success": True, "prompt_id": prompt_id, "message": "生成任务已提交，图片保存在 ComfyUI/output/"}
        return {"success": False, "error": resp.text}
    except requests.ConnectionError:
        return {"success": False, "error": "ComfyUI服务未启动，请先运行: cd G:\\AI_Tools\\ComfyUI && python main.py --cpu"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# === 一键生成短视频 ===
async def quick_short_video(script: str, voice: str = "zh-CN-XiaoxiaoNeural",
                            image_prompts: list = None, title: str = "AI视频") -> dict:
    """
    一键生成AI短视频流程（文案→配音→字幕→输出）
    
    参数:
    - script: 口播文案（每行一段，自动分句配字幕）
    - voice: Edge TTS 音色
    - image_prompts: 每段对应的AI生图提示词（可选）
    - title: 视频标题
    
    返回: {"success": bool, "audio": str, "srt": str}
    """
    import time
    
    project_dir = os.path.join(OUTPUT_DIR, f"quick_{int(time.time())}")
    os.makedirs(project_dir, exist_ok=True)
    
    results = {}
    
    # 1. 生成配音
    audio_path = os.path.join(project_dir, f"{title}_audio.mp3")
    tts_result = tts_generate(text=script, voice=voice, output=audio_path)
    results["audio"] = tts_result
    
    if not tts_result["success"]:
        return {"success": False, "step": "tts", "error": tts_result["error"]}
    
    # 2. 生成字幕
    import subprocess as sp
    # 获取音频时长
    probe = sp.run([FFMPEG_PATH, "-i", audio_path], capture_output=True, text=True)
    # 从stderr提取duration
    duration = 10.0  # 默认
    for line in probe.stderr.split('\n'):
        if "Duration" in line:
            import re
            m = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", line)
            if m:
                duration = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)) + int(m.group(4))/100
    
    srt_path = os.path.join(project_dir, f"{title}_subtitle.srt")
    srt_result = text_to_srt(text=script, duration=duration, output=srt_path)
    results["srt"] = srt_result
    
    results["project_dir"] = project_dir
    
    return {"success": True, **results, "message": f"配音和字幕已生成在 {project_dir}，如需合成视频请提供图片"}


# 工具注册
TOOLS = {
    "tts_generate": tts_generate,
    "video_from_images": video_from_images,
    "add_subtitle": add_subtitle,
    "video_concat": video_concat,
    "video_info": video_info,
    "text_to_srt": text_to_srt,
    "comfyui_generate": comfyui_generate,
    "quick_short_video": quick_short_video,
}
"""
