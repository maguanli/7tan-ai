# -*- coding: utf-8 -*-
"""
公众号发布插件 — 微信公众号爆款文章发布套件 📰
基于 tools/gzh_publish 桌面自动化脚本集（pyautogui 坐标点击 + 剪贴板粘贴 + OCR 验证）
工具:
  gzh_env_check       发布环境检查（依赖库/微信窗口/CDP）
  gzh_fill_form       填标题 + 作者
  gzh_paste_body      粘贴正文（文本文件 / 图文序列）
  gzh_set_digest      填摘要（120字内）
  gzh_set_cover       上传封面
  gzh_toggle_original 点击原创声明开关
  gzh_save_draft      保存草稿
  gzh_do_publish      发表（含弹窗确认）
  gzh_full_flow       全流程一键发布（可存草稿或直接发表）
  gzh_ocr_read        区域OCR（框选识别阅读量/界面文字，复用 region_ocr.py）
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# HERE = .../data/plugins/gzh_publish → 上3级 = 7tanAI 根目录
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
GZH_DIR = os.path.join(ROOT, 'tools', 'gzh_publish')
GZH_DO = os.path.join(GZH_DIR, 'gzh_do.py')

from src.tools.registry import register_tool


def _run(args_list, timeout=300):
    """调用统一入口脚本 gzh_do.py，返回 stdout"""
    if not os.path.exists(GZH_DO):
        return f'❌ 缺少发布入口脚本: {GZH_DO}\n请确认 tools/gzh_publish 套件完整。'
    cmd = [sys.executable, GZH_DO] + args_list
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace',
                           timeout=timeout, cwd=ROOT)
        out = r.stdout or ''
        if r.returncode != 0:
            out += '\n[stderr] ' + ((r.stderr or '')[-1500:])
        return out.strip() or f'（无输出，exit={r.returncode}）'
    except subprocess.TimeoutExpired:
        return '⏰ 执行超时。请确认：微信PC已登录、公众号编辑页已打开并显示在前台。'
    except Exception as e:
        return f'❌ 执行失败: {e}'


@register_tool(
    name="gzh_env_check",
    description="检查公众号发布环境：pyautogui/pyperclip/mss 等依赖库是否安装、微信PC窗口是否打开、CDP调试端口。每次发布前先调用此工具确认环境就绪。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="gzh_publish"
)
def gzh_env_check() -> str:
    """环境检查"""
    return _run(['check-env'], timeout=60)


@register_tool(
    name="gzh_fill_form",
    description="在微信公众号图文编辑器填入标题和作者（剪贴板粘贴，兼容中文）。发布前需微信公众平台编辑页已打开。可自定义坐标覆盖默认值。",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "文章标题（64字内）", "default": ""},
            "author": {"type": "string", "description": "作者名", "default": ""},
            "title_pos": {"type": "string", "description": "标题框坐标 x,y（默认 460,420）", "default": "460,420"},
            "author_pos": {"type": "string", "description": "作者框坐标 x,y（默认 410,462）", "default": "410,462"},
        },
        "required": ["title"],
    },
    category="gzh_publish"
)
def gzh_fill_form(title: str = "", author: str = "", title_pos: str = "460,420", author_pos: str = "410,462") -> str:
    """填标题+作者"""
    if not title.strip():
        return "请提供标题（--title）"
    args = ['fill-form', '--title', title]
    if author:
        args += ['--author', author]
    args += ['--title-pos', title_pos, '--author-pos', author_pos]
    return _run(args, timeout=60)


@register_tool(
    name="gzh_paste_body",
    description="在公众号编辑器粘贴正文。支持：--file 文本文件 / --text 直接文本 / --sequence 图文序列JSON（[{type:text,content:..},{type:img,file:xx.jpg}]）。图片从剪贴板粘贴（PowerShell Set-Clipboard）。",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "正文文本（与 file 二选一）", "default": ""},
            "file": {"type": "string", "description": "正文文本文件路径（与 text 二选一）", "default": ""},
            "sequence": {"type": "string", "description": "图文序列JSON文件路径", "default": ""},
            "img_dir": {"type": "string", "description": "sequence 图片所在目录", "default": ""},
            "body_pos": {"type": "string", "description": "正文区坐标 x,y（默认 500,560）", "default": "500,560"},
        },
        "required": [],
    },
    category="gzh_publish"
)
def gzh_paste_body(text: str = "", file: str = "", sequence: str = "", img_dir: str = "", body_pos: str = "500,560") -> str:
    """粘贴正文"""
    args = ['paste-body', '--body-pos', body_pos]
    if text:
        args += ['--text', text]
    elif file:
        args += ['--file', file]
    elif sequence:
        args += ['--sequence', sequence]
        if img_dir:
            args += ['--img-dir', img_dir]
    return _run(args, timeout=180)


@register_tool(
    name="gzh_set_digest",
    description="填入文章摘要（120字内，转发卡片显示）。",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "摘要文本（120字内）", "default": ""},
            "digest_pos": {"type": "string", "description": "摘要框坐标 x,y（默认 550,478）", "default": "550,478"},
        },
        "required": ["text"],
    },
    category="gzh_publish"
)
def gzh_set_digest(text: str = "", digest_pos: str = "550,478") -> str:
    """填摘要"""
    if not text.strip():
        return "请提供摘要文本"
    return _run(['set-digest', '--text', text, '--digest-pos', digest_pos], timeout=60)


@register_tool(
    name="gzh_set_cover",
    description="上传文章封面：点击封面区→点上传按钮→文件对话框粘贴封面路径回车。默认封面为套件内置 cover_900x383.png，可指定其他图片。",
    parameters={
        "type": "object",
        "properties": {
            "cover": {"type": "string", "description": "封面图片路径（默认套件内置 900x383 封面）", "default": ""},
            "cover_pos": {"type": "string", "description": "封面区坐标 x,y（默认 490,512）", "default": "490,512"},
            "upload_pos": {"type": "string", "description": "上传按钮坐标 x,y（默认 800,528）", "default": "800,528"},
        },
        "required": [],
    },
    category="gzh_publish"
)
def gzh_set_cover(cover: str = "", cover_pos: str = "490,512", upload_pos: str = "800,528") -> str:
    """上传封面"""
    args = ['set-cover', '--cover-pos', cover_pos, '--upload-pos', upload_pos]
    if cover:
        args += ['--cover', cover]
    return _run(args, timeout=120)


@register_tool(
    name="gzh_toggle_original",
    description="点击公众号编辑页的「原创声明」开关（750,518）。声明原创后文章受著作权保护并获得推荐加权。",
    parameters={
        "type": "object",
        "properties": {
            "on": {"type": "boolean", "description": "True=开启原创声明（默认）", "default": True},
            "original_pos": {"type": "string", "description": "原创开关坐标 x,y（默认 750,518）", "default": "750,518"},
        },
        "required": [],
    },
    category="gzh_publish"
)
def gzh_toggle_original(on: bool = True, original_pos: str = "750,518") -> str:
    """切换原创声明"""
    args = ['toggle-original', '--original-pos', original_pos]
    if on:
        args.append('--on')
    return _run(args, timeout=60)


@register_tool(
    name="gzh_save_draft",
    description="点击「保存为草稿」按钮（760,931），把当前编辑内容存为草稿（不发表，安全可复查）。",
    parameters={
        "type": "object",
        "properties": {
            "draft_pos": {"type": "string", "description": "保存草稿按钮坐标 x,y（默认 760,931）", "default": "760,931"},
        },
        "required": [],
    },
    category="gzh_publish"
)
def gzh_save_draft(draft_pos: str = "760,931") -> str:
    """保存草稿"""
    return _run(['save-draft', '--draft-pos', draft_pos], timeout=60)


@register_tool(
    name="gzh_do_publish",
    description="发表文章：点击发表按钮（保存草稿右侧第3个）+ 弹窗确认（458,456）。⚠️ 发表即群发，请先确认内容无误（可先用 gzh_save_draft 存草稿检查）。",
    parameters={
        "type": "object",
        "properties": {
            "draft_pos": {"type": "string", "description": "保存草稿按钮坐标（用于推算发表按钮位置）", "default": "760,931"},
            "confirm_pos": {"type": "string", "description": "发表弹窗确认按钮坐标 x,y（默认 458,456）", "default": "458,456"},
        },
        "required": [],
    },
    category="gzh_publish"
)
def gzh_do_publish(draft_pos: str = "760,931", confirm_pos: str = "458,456") -> str:
    """发表文章"""
    return _run(['publish', '--draft-pos', draft_pos, '--confirm-pos', confirm_pos], timeout=120)


@register_tool(
    name="gzh_full_flow",
    description="一键执行公众号发布全流程：填标题+作者 → 粘贴正文 → 填摘要 → 上传封面 → 勾选原创声明 → 保存草稿（默认不发表，--publish=True 才发表）。正文可用 file 指定文本文件。",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "文章标题（64字内）", "default": ""},
            "author": {"type": "string", "description": "作者", "default": ""},
            "file": {"type": "string", "description": "正文文本文件路径（默认套件 article_7tan_games.txt）", "default": ""},
            "text": {"type": "string", "description": "正文文本（与 file 二选一）", "default": ""},
            "digest": {"type": "string", "description": "摘要（120字内）", "default": ""},
            "cover": {"type": "string", "description": "封面图片路径", "default": ""},
            "publish": {"type": "boolean", "description": "True=最后直接发表；False=只存草稿（默认）", "default": False},
            "skip_cover": {"type": "boolean", "description": "True=跳过封面上传", "default": False},
            "skip_original": {"type": "boolean", "description": "True=跳过原创声明", "default": False},
        },
        "required": ["title"],
    },
    category="gzh_publish"
)
def gzh_full_flow(title: str = "", author: str = "", file: str = "", text: str = "",
                  digest: str = "", cover: str = "", publish: bool = False,
                  skip_cover: bool = False, skip_original: bool = False) -> str:
    """全流程发布"""
    if not title.strip():
        return "请提供文章标题"
    args = ['full-flow', '--title', title]
    if author:
        args += ['--author', author]
    if text:
        args += ['--text', text]
    elif file:
        args += ['--file', file]
    if digest:
        args += ['--digest', digest]
    if cover:
        args += ['--cover', cover]
    if publish:
        args.append('--publish')
    if skip_cover:
        args.append('--skip-cover')
    if skip_original:
        args.append('--skip-original')
    return _run(args, timeout=600)


@register_tool(
    name="gzh_ocr_read",
    description="区域OCR识别：框选屏幕区域（--select 鼠标拖框）或指定区域（--region x,y,w,h）识别文字。用于读取微信文章底部「阅读量」数字、界面按钮文字等。基于 region_ocr.py（区域裁剪+缩放，不烧CPU）。",
    parameters={
        "type": "object",
        "properties": {
            "select": {"type": "boolean", "description": "True=鼠标框选区域（默认）", "default": True},
            "region": {"type": "string", "description": "指定区域 x,y,w,h（与 select 二选一）", "default": ""},
            "scale": {"type": "number", "description": "识别缩放（0.5=半分辨率加速）", "default": 0},
        },
        "required": [],
    },
    category="gzh_publish"
)
def gzh_ocr_read(select: bool = True, region: str = "", scale: float = 0) -> str:
    """区域OCR读阅读量/界面文字"""
    args = ['ocr-read']
    if select and not region:
        args.append('--select')
    elif region:
        args += ['--region', region]
    if scale:
        args += ['--scale', str(scale)]
    return _run(args, timeout=180)
