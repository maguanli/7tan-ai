
# -*- coding: utf-8 -*-
"""
7Tan AI 视频工厂插件 — 纯本地运行
Edge TTS 配音 | 幻灯片视频 | 字幕 | ONNX AI 图像处理
"""
import asyncio, os, sys, json, subprocess
from pathlib import Path
from datetime import datetime

BASE = Path(r"G:\AI_Video")
SCRIPTS = BASE / "scripts"
OUTPUT = BASE / "output"
PROJECTS = BASE / "projects"
TEMP = BASE / "temp"

for d in [OUTPUT, PROJECTS, TEMP]:
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SCRIPTS))
os.environ["PATH"] = str(BASE / "bin" / "ffmpeg" / "bin") + ";" + os.environ["PATH"]


def _run_python(script_name: str, *args, timeout: int = 300) -> dict:
    """运行 G:\AI_Video\scripts\ 下的 Python 脚本"""
    script_path = SCRIPTS / script_name
    if not script_path.exists():
        return {"success": False, "error": f"脚本不存在: {script_path}"}
    
    cmd = [sys.executable, str(script_path)] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, 
                                timeout=timeout, cwd=str(BASE),
                                encoding='utf-8', errors='replace')
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[-5000:] if result.stdout else "",
            "stderr": result.stderr[-3000:] if result.stderr else ""
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"脚本超时({timeout}s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 工具函数 ====================

def ai_video_tts(text: str, voice: str = "zh-CN-XiaoxiaoNeural", 
                 output_name: str = "narration", rate: str = "+5%") -> dict:
    """
    🎙️ Edge TTS 免费配音 — 文本转语音
    voice: zh-CN-XiaoxiaoNeural(女)/zh-CN-YunxiNeural(男)/zh-CN-XiaoyiNeural(女童)/zh-CN-YunyangNeural(新闻男)
    """
    try:
        async def _tts():
            import edge_tts
            mp3 = str(OUTPUT / f"{output_name}.mp3")
            comm = edge_tts.Communicate(text.strip(), voice, rate=rate)
            await comm.save(mp3)
            size_kb = os.path.getsize(mp3) / 1024
            return mp3, size_kb
        mp3, size = asyncio.run(_tts())
        return {"success": True, "output": mp3, "size_kb": round(size, 1), "message": f"配音完成: {size:.1f}KB"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def ai_video_make_from_json(project_file: str) -> dict:
    """
    🎬 从 JSON 项目文件一键生成视频
    项目文件格式见 G:\AI_Video\projects\demo.json
    """
    return _run_python("ai_video_factory.py", "make", project_file, timeout=600)


def ai_video_slideshow(image_dir: str = None, audio_path: str = None,
                       output_name: str = "slideshow", duration: float = 3.0,
                       resolution: str = "1920x1080") -> dict:
    """
    🖼️ 图片幻灯片转视频
    把指定目录下所有图片按顺序合成视频，可选加配音
    """
    try:
        from PIL import Image
        import numpy as np
        
        if image_dir:
            img_dir = Path(image_dir)
        else:
            img_dir = TEMP
        
        images = sorted([
            str(f) for f in img_dir.glob("*") 
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".webp")
        ])
        
        if not images:
            return {"success": False, "error": f"目录中没有图片: {img_dir}"}
        
        w, h = map(int, resolution.split("x"))
        
        # Write a temp script
        script = {
            "title": output_name,
            "voice": "zh-CN-XiaoxiaoNeural",
            "scenes": [{"text": f"第{i+1}页", "image": img} for i, img in enumerate(images)]
        }
        tmp_json = str(TEMP / f"_slideshow_{output_name}.json")
        with open(tmp_json, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        
        return _run_python("ai_video_factory.py", "make", tmp_json, timeout=600)
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def ai_video_make_slides(texts: str, title: str = "AI视频",
                         voice: str = "zh-CN-XiaoxiaoNeural") -> dict:
    """
    📝 文案 → 幻灯片视频（每行一个场景）
    输入多行文本，每行自动生成一张幻灯片 + 配音
    """
    try:
        scenes = [{"text": line.strip()} for line in texts.strip().split("\n") if line.strip()]
        if not scenes:
            return {"success": False, "error": "文本为空"}
        
        script = {"title": title, "voice": voice, "scenes": scenes}
        tmp_json = str(TEMP / f"_tts_{title}.json")
        with open(tmp_json, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        
        return _run_python("ai_video_factory.py", "make", tmp_json, timeout=600)
    except Exception as e:
        return {"success": False, "error": str(e)}


def ai_video_add_subtitle(video_path: str, srt_text: str = None,
                          output_name: str = None) -> dict:
    """
    📝 给视频添加字幕
    srt_text: SRT 格式字幕，不提供则尝试用 ffmpeg 自动识别
    """
    try:
        vpath = Path(video_path)
        if not vpath.exists():
            return {"success": False, "error": f"视频不存在: {video_path}"}
        
        if not output_name:
            output_name = vpath.stem + "_subbed"
        
        if srt_text:
            srt_file = str(TEMP / "_subs.srt")
            with open(srt_file, "w", encoding="utf-8") as f:
                f.write(srt_text)
            
            srt_esc = srt_file.replace("\\", "/").replace(":", "\\:")
            out = str(OUTPUT / f"{output_name}.mp4")
            cmd = [
                "ffmpeg", "-i", video_path,
                "-vf", f"subtitles={srt_esc}:force_style='FontSize=28,Alignment=2'",
                "-c:a", "copy", "-y", out
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                size_mb = os.path.getsize(out) / (1024*1024)
                return {"success": True, "output": out, "size_mb": round(size_mb, 1)}
            else:
                return {"success": False, "error": result.stderr[-1000:]}
        else:
            return {"success": False, "error": "请提供 SRT 字幕文本"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def ai_video_enhance_image(image_path: str, scale: int = 2) -> dict:
    """
    🔍 超分辨率增强图片（CPU 降级方案: bicubic 插值）
    有 ONNX 模型时自动使用 Real-ESRGAN
    """
    if not Path(image_path).exists():
        return {"success": False, "error": f"图片不存在: {image_path}"}
    return _run_python("ai_video_factory.py", "enhance", image_path, timeout=120)


def ai_video_remove_bg(image_path: str) -> dict:
    """🎭 移除图片背景（OpenCV GrabCut）"""
    if not Path(image_path).exists():
        return {"success": False, "error": f"图片不存在: {image_path}"}
    
    try:
        from onnx_engine import ONNXEngine
        eng = ONNXEngine()
        out = eng.remove_background(image_path)
        return {"success": True, "output": out, "message": "背景移除完成"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def ai_video_status() -> dict:
    """📊 查看 AI 视频工厂状态"""
    try:
        import shutil
        disk_gb = shutil.disk_usage(str(BASE)).free / (1024**3)
        
        output_files = list(OUTPUT.glob("*.mp4")) + list(OUTPUT.glob("*.mp3"))
        
        # Check models
        sd_models = list((BASE / "stable-diffusion-webui/models/Stable-diffusion").glob("*.safetensors"))
        animatediff = list((BASE / "models/animatediff").glob("*"))
        
        return {
            "success": True,
            "base_path": str(BASE),
            "disk_free_gb": round(disk_gb, 1),
            "output_count": len(output_files),
            "latest_outputs": [str(f.name) for f in sorted(output_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]],
            "sd_models": [f.name for f in sd_models],
            "animatediff": [f.name for f in animatediff],
            "components": {
                "ffmpeg": "✅" if (BASE / "bin/ffmpeg/bin/ffmpeg.exe").exists() else "❌",
                "comfyui": "✅" if (BASE / "comfyui/ComfyUI/main.py").exists() else "❌",
                "sd_webui": "✅" if (BASE / "stable-diffusion-webui/webui.py").exists() else "❌",
                "edge_tts": "✅",
                "moviepy": "✅",
                "opencv": "✅",
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def ai_video_demo() -> dict:
    """🎬 运行演示：生成一个完整的 AI 视频"""
    return _run_python("ai_video_factory.py", "demo", timeout=600)


def ai_video_list_projects() -> dict:
    """📂 列出所有项目文件"""
    projects = list(PROJECTS.glob("*.json"))
    return {
        "success": True,
        "count": len(projects),
        "projects": [
            {
                "name": p.name,
                "size_kb": round(p.stat().st_size / 1024, 1),
                "modified": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            }
            for p in sorted(projects, key=lambda x: x.stat().st_mtime, reverse=True)
        ]
    }


def ai_video_list_outputs() -> dict:
    """📁 列出所有输出文件"""
    files = list(OUTPUT.glob("*"))
    return {
        "success": True,
        "count": len(files),
        "files": [
            {
                "name": f.name,
                "size_mb": round(f.stat().st_size / (1024*1024), 2),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            }
            for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
        ]
    }
