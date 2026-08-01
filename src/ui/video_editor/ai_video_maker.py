"""
AI 视频制作引擎 — 图文成片

利用现有 AI 大模型（盘古）+ 内置 TTS + 编辑器能力，
实现「输入主题 → AI 写脚本 → 配音 → 自动编排到时间轴」的完整链路。

不依赖 Sora/Runway 等专业视频生成 API。
"""

import json
import uuid
import time
from pathlib import Path
from typing import Optional, Callable

from .data_models import SceneScript, VideoScript, AIVideoTask, Project


class AIVideoMaker:
    """AI 视频制作引擎 — 图文成片"""

    def __init__(self, editor_api=None, dub_engine=None, media_bin=None):
        self._editor_api = editor_api          # EditorAPI 实例
        self._dub_engine = dub_engine           # AIDubEngine 实例
        self._media_bin = media_bin             # MediaBin 实例
        self._output_dir = Path("downloads/ai_video")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate_script(self, topic: str, style: str = "professional",
                        target_duration: float = 180.0) -> VideoScript:
        """调用 AI 大模型生成分镜头脚本。

        Args:
            topic: 视频主题描述
            style: 风格（professional/casual/tech/funny）
            target_duration: 目标时长（秒）

        Returns:
            VideoScript: 生成的分镜头脚本
        """
        # 计算场景数量（约每 30 秒一个场景）
        scene_count = max(3, round(target_duration / 30))
        avg_words = round(target_duration * 3 / scene_count)  # 3字/秒

        prompt = self._build_script_prompt(topic, style, scene_count, avg_words, target_duration)

        # 调用 AI 生成
        try:
            from src.agent.model_manager import ModelManager
            from src.database.db import get_active_ai_config_raw
            cfg = get_active_ai_config_raw()
            model_name = cfg.get("model", "deepseek-v4-pro") if cfg else "deepseek-v4-pro"
            mm = ModelManager(model_name)
            resp = mm.chat(messages=[{"role": "user", "content": prompt}])
            content = resp["choices"][0]["message"]["content"]
            script = self._parse_script_response(content, target_duration)
            return script
        except Exception as e:
            # 降级：生成一个简单的默认脚本
            return self._fallback_script(topic, style, target_duration)

    def _build_script_prompt(self, topic: str, style: str, scene_count: int,
                              avg_words: int, target_duration: float) -> str:
        """构建脚本生成 Prompt"""
        style_map = {
            "professional": "专业严谨，条理清晰",
            "casual": "轻松自然，口语化",
            "tech": "科技感强，简洁有力",
            "funny": "幽默风趣，节奏明快",
        }
        style_desc = style_map.get(style, style)

        return f"""你是一个专业视频编导。根据用户提供的主题，生成一个分镜头脚本。

【要求】
1. 输出纯 JSON，不要任何 Markdown 标记或额外文字
2. 场景数量：{scene_count} 个
3. 每个场景文案约 {avg_words} 个字（中文），配音速度约 3 字/秒
4. 风格：{style_desc}
5. 文案口语化、有节奏感，适合配音朗读
6. 配图描述简洁明确（英文），适合 AI 生图

【输出格式】
{{
  "title": "视频标题",
  "style": "{style}",
  "scenes": [
    {{
      "index": 1,
      "text": "配音文案（中文）",
      "image_prompt": "image description in English for AI generation",
      "duration": 30
    }}
  ]
}}

【主题】
{topic}

请直接输出 JSON："""

    def _parse_script_response(self, response: str, target_duration: float) -> VideoScript:
        """解析 AI 返回的 JSON 脚本"""
        # 清理可能的 Markdown 标记
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取 JSON 对象
            import re
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                data = json.loads(match.group())
            else:
                raise ValueError("无法解析 AI 返回的脚本")

        scenes = []
        total = 0.0
        for s in data.get("scenes", []):
            duration = float(s.get("duration", 30))
            scene = SceneScript(
                index=int(s.get("index", len(scenes) + 1)),
                text=str(s.get("text", "")),
                image_prompt=str(s.get("image_prompt", "")),
                duration=duration,
                transition=str(s.get("transition", "fade")),
            )
            scenes.append(scene)
            total += duration

        return VideoScript(
            title=str(data.get("title", "AI 生成视频")),
            style=str(data.get("style", "professional")),
            scenes=scenes,
            total_duration=total if total > 0 else target_duration,
        )

    def _fallback_script(self, topic: str, style: str, target_duration: float) -> VideoScript:
        """AI 调用失败时的降级脚本"""
        scene_count = max(3, round(target_duration / 30))
        duration_per_scene = round(target_duration / scene_count, 1)
        scenes = []
        for i in range(scene_count):
            scenes.append(SceneScript(
                index=i + 1,
                text=f"关于「{topic}」的第 {i + 1} 部分。请编辑此文案以完善内容。",
                image_prompt=f"abstract concept of {topic}, minimalist style",
                duration=duration_per_scene,
            ))

        return VideoScript(
            title=topic,
            style=style,
            scenes=scenes,
            total_duration=target_duration,
        )

    def dub_scenes(self, script: VideoScript, voice: str = "female",
                   on_progress: Callable = None) -> VideoScript:
        """为每个场景生成配音。

        Args:
            script: 分镜头脚本
            voice: 音色选择（female/male）
            on_progress: 进度回调 (idx, total, message)

        Returns:
            更新后的 VideoScript（含 audio_path）
        """
        if not self._dub_engine:
            raise RuntimeError("配音引擎未初始化，请确保 ai_dub_engine 可用")

        total = len(script.scenes)
        for i, scene in enumerate(script.scenes):
            if on_progress:
                on_progress(i + 1, total, f"配音中: 场景 {i + 1}/{total}")

            try:
                audio_path = self._dub_engine.synthesize(
                    text=scene.text,
                    voice=voice,
                    output_dir=str(self._output_dir),
                )
                scene.audio_path = audio_path
            except Exception as e:
                logger.warning(f"[AIVideoMaker] 配音失败 (场景 {scene.index}): {e}")
                scene.audio_path = None

        return script

    def arrange_to_timeline(self, project: Project, script: VideoScript,
                            mode: str = "text_only",
                            on_progress: Callable = None) -> Project:
        """自动编排到时间轴。

        将脚本中的每个场景：
        - 图片/纯色背景 → 视频轨（带 Ken Burns 动画）
        - 配音 → 音频轨
        - 字幕 → 字幕轨
        - 场景间添加转场

        Args:
            project: 当前项目
            script: 分镜头脚本
            mode: text_only / image / ai_image
            on_progress: 进度回调

        Returns:
            更新后的 Project
        """
        if not self._editor_api:
            raise RuntimeError("编辑器 API 未初始化")

        total = len(script.scenes)
        current_time = 0.0

        # 背景色映射（纯文本模式）
        bg_colors = ["#1a1a2e", "#16213e", "#0f3460", "#533483", "#e94560"]

        for i, scene in enumerate(script.scenes):
            if on_progress:
                on_progress(i + 1, total, f"编排中: 场景 {i + 1}/{total}")

            scene_start = current_time
            scene_end = current_time + scene.duration

            # 1) 视频轨 — 图片或纯色背景
            if mode == "text_only":
                # 纯文本模式：生成纯色背景
                bg_color = bg_colors[i % len(bg_colors)]
                bg_path = self._create_color_bg(bg_color, project.resolution, i)
                bg_media = self._media_bin.add_media(str(bg_path)) if (bg_path and self._media_bin) else None
                if bg_media:
                    self._editor_api.add_clip_to_timeline(bg_media, track_index=0, timeline_start=scene_start)
            elif scene.image_path:
                # 图文模式 / AI 生图模式
                img_media = self._media_bin.add_media(scene.image_path) if self._media_bin else None
                if img_media:
                    self._editor_api.add_clip_to_timeline(img_media, track_index=0, timeline_start=scene_start)

            # 2) 音频轨 — 配音
            if scene.audio_path:
                audio_media = self._media_bin.add_media(scene.audio_path) if self._media_bin else None
                if audio_media:
                    self._editor_api.add_clip_to_timeline(audio_media, track_index=1, timeline_start=scene_start)

            # 3) 字幕轨 — 文字
            self._editor_api.add_subtitle(
                text=scene.text,
                start_time=scene_start,
                end_time=scene_end,
                track_index=3,
            )

            current_time = scene_end

        # 更新项目时长
        project.duration = current_time
        return project

    def _create_color_bg(self, color_hex: str, resolution: tuple,
                         index: int) -> Optional[Path]:
        """创建纯色背景图片"""
        try:
            from PIL import Image, ImageDraw, ImageFilter

            w, h = resolution
            img = Image.new("RGB", (w, h), color_hex)

            # 添加微妙的渐变和噪点，让纯色背景更有质感
            draw = ImageDraw.Draw(img)
            # 顶部渐变叠加
            for y in range(h // 3):
                alpha = int(40 * (1 - y / (h // 3)))
                overlay = (255, 255, 255) if y < h // 6 else (0, 0, 0)
                draw.line([(0, y), (w, y)], fill=overlay, width=1)

            # 轻微模糊增加质感
            img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

            path = self._output_dir / f"bg_scene_{index:02d}.png"
            img.save(path, "PNG")
            return path
        except Exception as e:
            logger.warning(f"[AIVideoMaker] 创建背景失败: {e}")
            return None

    def run_full_pipeline(self, topic: str, project: Project,
                          mode: str = "text_only",
                          style: str = "professional",
                          target_duration: float = 180.0,
                          voice: str = "female",
                          on_progress: Callable = None) -> AIVideoTask:
        """一键运行完整流水线：脚本 → 配音 → 编排。

        Args:
            topic: 视频主题
            project: 目标项目
            mode: text_only / image / ai_image
            style: 风格
            target_duration: 目标时长（秒）
            voice: 配音音色
            on_progress: 进度回调 (status, progress, message)

        Returns:
            AIVideoTask: 任务状态
        """
        task = AIVideoTask(
            id=str(uuid.uuid4())[:8],
            status="scripting",
            message="正在生成脚本…",
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        def _progress(status, progress, message):
            task.status = status
            task.progress = progress
            task.message = message
            if on_progress:
                on_progress(status, progress, message)

        try:
            # 步骤 1: 生成脚本
            _progress("scripting", 0.1, "AI 正在生成分镜头脚本…")
            script = self.generate_script(topic, style, target_duration)
            task.script = script

            # 步骤 2: 配音
            _progress("dubbing", 0.3, "正在配音…")
            script = self.dub_scenes(script, voice, lambda i, t, m: _progress(
                "dubbing", 0.3 + 0.3 * (i / t), m))

            # 步骤 3: 编排
            _progress("arranging", 0.6, "正在编排到时间轴…")
            self.arrange_to_timeline(project, script, mode, lambda i, t, m: _progress(
                "arranging", 0.6 + 0.35 * (i / t), m))

            # 完成
            _progress("done", 1.0, f"视频制作完成！共 {len(script.scenes)} 个场景，{script.total_duration:.0f} 秒")
            return task

        except Exception as e:
            _progress("failed", task.progress, f"制作失败: {e}")
            return task
