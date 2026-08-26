# -*- coding: utf-8 -*-
"""
摄像头视觉插件 📷 — 7Tan 桌面机器人的"眼睛"
基于 tools/camera_vision/camera_do.py（OpenCV 采集 + 智谱 GLM-4.6V 视觉大模型理解）

工具:
  camera_list             枚举摄像头设备
  camera_capture          摄像头拍照保存到本地
  camera_see              📸 拍照 + 视觉大模型理解（核心：看懂真实世界）
  vision_analyze_image    用视觉大模型分析任意图片/截图（无需摄像头）
  camera_watch            连续监控：帧差变化检测 + 触发视觉理解

无摄像头时 camera_see 自动降级为屏幕截图 + 视觉理解，保证能力可用。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # 7tanAI 根目录
DO = os.path.join(ROOT, 'tools', 'camera_vision', 'camera_do.py')

from src.tools.registry import register_tool

CREATE_NO_WINDOW = 0x08000000


def _run(args_list, timeout=120):
    """调用后端脚本 camera_do.py，返回 stdout"""
    if not os.path.exists(DO):
        return f'❌ 缺少摄像头视觉脚本: {DO}'
    import subprocess
    cmd = [sys.executable, DO] + args_list
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace',
                           timeout=timeout, cwd=ROOT,
                           creationflags=CREATE_NO_WINDOW)
        out = r.stdout or ''
        if r.returncode != 0:
            out += '\n[stderr] ' + ((r.stderr or '')[-1500:])
        return out.strip() or f'（无输出，exit={r.returncode}）'
    except subprocess.TimeoutExpired:
        return '⏰ 执行超时。请检查摄像头是否被其他程序占用。'
    except Exception as e:
        return f'❌ 执行失败: {e}'


@register_tool(
    name="camera_list",
    description="枚举本机摄像头设备（编号、分辨率）。用于确认机器人是否有可用的'眼睛'硬件。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="vision"
)
def camera_list() -> str:
    """枚举摄像头设备"""
    return _run(['list'], timeout=60)


@register_tool(
    name="camera_capture",
    description="用摄像头拍照并保存到本地（默认1280x720）。可指定设备编号和分辨率。返回图片路径。",
    parameters={
        "type": "object",
        "properties": {
            "index": {"type": "integer", "description": "摄像头编号，默认-1=自动寻找第一个可用设备", "default": -1},
            "save": {"type": "string", "description": "保存路径（默认 data/camera_vision/ 下自动命名）", "default": ""},
            "width": {"type": "integer", "description": "分辨率宽", "default": 1280},
            "height": {"type": "integer", "description": "分辨率高", "default": 720},
        },
        "required": [],
    },
    category="vision"
)
def camera_capture(index: int = -1, save: str = "", width: int = 1280, height: int = 720) -> str:
    """摄像头拍照"""
    args = ['capture', '--index', str(index), '--width', str(width), '--height', str(height)]
    if save:
        args += ['--save', save]
    return _run(args, timeout=90)


@register_tool(
    name="camera_see",
    description="📸 机器人的眼睛：摄像头拍照 + 视觉大模型（GLM-4.6V）理解画面，输出结构化JSON（场景/物体/人物/文字/异常/建议）。无摄像头时自动降级为屏幕截图+视觉理解。用于机器人'看'真实世界。",
    parameters={
        "type": "object",
        "properties": {
            "index": {"type": "integer", "description": "摄像头编号，默认-1=自动", "default": -1},
            "image": {"type": "string", "description": "直接分析已有图片路径（跳过拍照）", "default": ""},
            "prompt": {"type": "string", "description": "自定义理解指令（如'桌面上有什么？'）", "default": ""},
        },
        "required": [],
    },
    category="vision"
)
def camera_see(index: int = -1, image: str = "", prompt: str = "") -> str:
    """拍照 + 视觉大模型理解"""
    args = ['see', '--index', str(index)]
    if image:
        args += ['--image', image]
    if prompt:
        args += ['--prompt', prompt]
    return _run(args, timeout=120)


@register_tool(
    name="vision_analyze_image",
    description="用视觉大模型（GLM-4.6V）分析任意图片/截图文件：识别物体、场景、文字、人物、异常。不依赖摄像头，适合分析下载的截图、封面图、验证码等。",
    parameters={
        "type": "object",
        "properties": {
            "image": {"type": "string", "description": "图片文件路径（png/jpg）"},
            "prompt": {"type": "string", "description": "自定义理解指令（默认输出结构化描述）", "default": ""},
        },
        "required": ["image"],
    },
    category="vision"
)
def vision_analyze_image(image: str, prompt: str = "") -> str:
    """分析任意图片"""
    args = ['analyze', '--image', image]
    if prompt:
        args += ['--prompt', prompt]
    return _run(args, timeout=120)


@register_tool(
    name="camera_watch",
    description="👁️ 连续监控模式：摄像头按间隔拍照，用帧差检测画面变化（如有人经过/物体移动），变化时保存图片并可触发视觉大模型理解。适合安防巡检、无人值守监控。",
    parameters={
        "type": "object",
        "properties": {
            "index": {"type": "integer", "description": "摄像头编号，默认-1=自动", "default": -1},
            "seconds": {"type": "integer", "description": "监控总时长（秒）", "default": 30},
            "interval": {"type": "integer", "description": "拍照间隔（秒）", "default": 5},
            "threshold": {"type": "number", "description": "变化触发阈值 0~1（画面差异比例，默认0.05）", "default": 0.05},
            "use_vlm": {"type": "boolean", "description": "变化时是否调用视觉大模型理解（默认true）", "default": True},
        },
        "required": [],
    },
    category="vision"
)
def camera_watch(index: int = -1, seconds: int = 30, interval: int = 5, threshold: float = 0.05, use_vlm: bool = True) -> str:
    """连续监控"""
    args = ['watch', '--index', str(index), '--seconds', str(seconds),
            '--interval', str(interval), '--threshold', str(threshold)]
    if use_vlm:
        args += ['--vlm']
    return _run(args, timeout=seconds + 60)
