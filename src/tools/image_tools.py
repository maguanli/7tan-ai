"""
图片处理工具 — 压缩、调整尺寸、格式转换
"""
from pathlib import Path

from loguru import logger
from .registry import register_tool


@register_tool(
    name="compress_image",
    description="压缩图片（LOGO/截图），减小体积。支持调整尺寸和质量。",
    parameters={
        "type": "object",
        "properties": {
            "input_path": {"type": "string", "description": "输入图片路径"},
            "output_path": {"type": "string", "description": "输出图片路径（可选，默认覆盖）"},
            "max_width": {"type": "integer", "description": "最大宽度(px)", "default": 1920},
            "max_height": {"type": "integer", "description": "最大高度(px)", "default": 1920},
            "quality": {"type": "integer", "description": "JPEG 质量 1-100", "default": 85},
        },
        "required": ["input_path"]
    },
    category="image",
)
def compress_image(input_path: str, output_path: str = None, max_width: int = 1920,
                   max_height: int = 1920, quality: int = 85) -> str:
    """压缩图片"""
    from PIL import Image

    inp = Path(input_path)
    if not inp.exists():
        return f"❌ 图片不存在: {input_path}"

    out = Path(output_path) if output_path else inp

    try:
        img = Image.open(inp)

        # 转换为 RGB（处理 RGBA/PNG）
        if img.mode in ("RGBA", "P"):
            # PNG 有透明通道，保留为 PNG
            if img.mode == "RGBA":
                out = out.with_suffix(".png")
                # 如果有透明通道，用 PNG 保存
                img.thumbnail((max_width, max_height), Image.LANCZOS)
                img.save(out, "PNG", optimize=True)
                return f"✅ 图片已优化: {out} ({_size_str(inp)} → {_size_str(out)})"
            img = img.convert("RGB")

        # 调整尺寸
        img.thumbnail((max_width, max_height), Image.LANCZOS)

        # 保存
        out = out.with_suffix(".jpg")
        img.save(out, "JPEG", quality=quality, optimize=True)

        size_before = inp.stat().st_size
        size_after = out.stat().st_size
        saved = (1 - size_after / size_before) * 100 if size_before > 0 else 0

        logger.info(f"🖼️ 图片压缩: {_size_str(inp)} → {_size_str(out)} (节省 {saved:.0f}%)")
        return f"✅ 图片已压缩: {out}\n  {_size_str(inp)} → {_size_str(out)} (节省 {saved:.0f}%)"
    except Exception as e:
        return f"❌ 图片处理失败: {e}"


def _size_str(p: Path) -> str:
    """文件大小字符串"""
    size = p.stat().st_size
    for unit in ["B", "KB", "MB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"
