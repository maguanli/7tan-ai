# -*- coding: utf-8 -*-
"""
gzh_publish — Linux（含鸿蒙PC Linux生态）平台变体

公众号发布依赖「Windows 版微信 PC 客户端」（桌面自动化：坐标点击 + OCR 验证）。
Linux / 鸿蒙PC 无法操作微信 PC 客户端，因此本变体所有工具返回友好提示：
  - 用 Windows 版 7Tan 完成公众号发布
  - 或登录网页版公众号后台（mp.weixin.qq.com）手动发布

与 Windows 版保持同名工具函数（gzh_xxx），上层调用无需改动。
"""
import sys
from src.tools.registry import register_tool

_MSG = (
    "❌ 公众号发布仅支持 Windows 版 7Tan（需要微信 PC 客户端）。\n"
    f"当前系统：{sys.platform}。\n"
    "解决办法：① 在 Windows 电脑上使用 7Tan 绿色版完成公众号发布；"
    "② 或直接登录网页版公众号后台（mp.weixin.qq.com）手动发布。"
)


def _unsupported() -> str:
    return _MSG


@register_tool(
    name="gzh_env_check",
    description="公众号发布环境检查（当前系统不可用，返回指引）。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="publish"
)
def gzh_env_check() -> str:
    return _unsupported()


@register_tool(
    name="gzh_fill_form",
    description="公众号编辑器填入标题和作者（当前系统不可用，返回指引）。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="publish"
)
def gzh_fill_form() -> str:
    return _unsupported()


@register_tool(
    name="gzh_paste_body",
    description="公众号编辑器粘贴正文（当前系统不可用，返回指引）。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="publish"
)
def gzh_paste_body() -> str:
    return _unsupported()


@register_tool(
    name="gzh_set_digest",
    description="公众号填入文章摘要（当前系统不可用，返回指引）。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="publish"
)
def gzh_set_digest() -> str:
    return _unsupported()


@register_tool(
    name="gzh_set_cover",
    description="公众号上传文章封面（当前系统不可用，返回指引）。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="publish"
)
def gzh_set_cover() -> str:
    return _unsupported()


@register_tool(
    name="gzh_toggle_original",
    description="公众号点击原创声明开关（当前系统不可用，返回指引）。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="publish"
)
def gzh_toggle_original() -> str:
    return _unsupported()


@register_tool(
    name="gzh_save_draft",
    description="公众号保存草稿（当前系统不可用，返回指引）。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="publish"
)
def gzh_save_draft() -> str:
    return _unsupported()


@register_tool(
    name="gzh_do_publish",
    description="公众号发表文章（当前系统不可用，返回指引）。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="publish"
)
def gzh_do_publish() -> str:
    return _unsupported()


@register_tool(
    name="gzh_full_flow",
    description="公众号全流程一键发布（当前系统不可用，返回指引）。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="publish"
)
def gzh_full_flow() -> str:
    return _unsupported()


@register_tool(
    name="gzh_ocr_read",
    description="公众号区域OCR识别（当前系统不可用，返回指引）。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="publish"
)
def gzh_ocr_read() -> str:
    return _unsupported()
