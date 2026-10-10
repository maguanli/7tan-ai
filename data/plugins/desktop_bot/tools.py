# -*- coding: utf-8 -*-
"""
通用桌面机器人插件 🤖 — 屏幕自动化通用能力（微信/QQ/任意桌面软件）
基于 tools/desktop_bot/desktop_do.py（mss 截图 + Windows OCR 定位 + pyautogui 键鼠 + win32 剪贴板）
工具:
  desktop_env_check     环境检查（依赖库/OCR 引擎/窗口）
  desktop_windows       列出可见窗口
  desktop_activate      激活窗口（标题模糊匹配）
  desktop_screenshot    全屏/区域截图
  desktop_ocr           屏幕 OCR（文字+坐标）
  desktop_click_text    按文字定位点击（OCR 找字→点字）
  desktop_click_pos     按坐标点击
  desktop_type_text     输入文本（剪贴板直写，毫秒级）
  desktop_paste_image   粘贴图片到当前焦点
  desktop_hotkey        发送组合键
  desktop_verify        验证屏幕是否出现文字
  desktop_send_chat     通用聊天发送（激活→搜索→输入→发送→验证）
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # 7tanAI 根目录
DO = os.path.join(ROOT, 'tools', 'desktop_bot', 'desktop_do.py')

from src.tools.registry import register_tool

CREATE_NO_WINDOW = 0x08000000


def _run(args_list, timeout=120):
    """调用统一入口脚本 desktop_do.py，返回 stdout（支持用户中止：杀进程树）"""
    if not os.path.exists(DO):
        return f'❌ 缺少桌面机器人脚本: {DO}'
    cmd = [sys.executable, DO] + args_list
    try:
        from src.utils.abort_signal import run_with_abort, AbortedError
        try:
            rc, so, se = run_with_abort(cmd, cwd=ROOT, timeout=timeout)
        except AbortedError:
            return '⏹ 已中止（用户终止任务），桌面操作已强制结束'
        out = so or ''
        if rc != 0:
            out += '\n[stderr] ' + ((se or '')[-1500:])
        return out.strip() or f'（无输出，exit={rc}）'
    except subprocess.TimeoutExpired:
        return '⏰ 执行超时。请确认目标软件窗口已打开并显示在前台。'
    except Exception as e:
        return f'❌ 执行失败: {e}'


@register_tool(
    name="desktop_env_check",
    description="检查桌面机器人环境：mss/PIL/pyautogui/win32clipboard/winrt 依赖是否安装、Windows OCR 引擎是否可用、可见窗口列表。每次桌面自动化前先调用。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="desktop"
)
def desktop_env_check() -> str:
    """环境检查"""
    return _run(['check-env'], timeout=60)


@register_tool(
    name="desktop_windows",
    description="列出当前桌面所有可见窗口（可带关键字过滤）。用于确认目标软件（微信等）是否打开、窗口标题是什么。",
    parameters={
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "标题关键字过滤（如 微信），留空列出全部", "default": ""},
        },
        "required": [],
    },
    category="desktop"
)
def desktop_windows(keyword: str = "") -> str:
    """列出窗口"""
    args = ['windows']
    if keyword:
        args += ['--keyword', keyword]
    return _run(args, timeout=30)


@register_tool(
    name="desktop_snapshot",
    description="获取桌面结构化快照（最快看明白桌面）：前台窗口标题+位置、可见窗口列表(标题/坐标/大小/是否前台)、前台窗口区域 OCR 文字摘要（带坐标）。一次调用代替 截图+全屏OCR：窗口信息毫秒级、OCR只跑活动窗口区域（比全屏快5~10倍）、输出精简JSON token消耗小。桌面自动化第一步建议用它。",
    parameters={
        "type": "object",
        "properties": {
            "top": {"type": "integer", "description": "最多返回窗口数", "default": 12},
            "ocr_top": {"type": "integer", "description": "OCR 摘要最多行数", "default": 25},
            "region": {"type": "string", "description": "指定 OCR 区域 x,y,w,h（默认=前台窗口区域）", "default": ""},
        },
        "required": [],
    },
    category="desktop"
)
def desktop_snapshot(top: int = 12, ocr_top: int = 25, region: str = "") -> str:
    """桌面快照（结构化摘要）"""
    args = ['snapshot', '--top', str(top), '--ocr-top', str(ocr_top)]
    if region:
        args += ['--region', region]
    return _run(args, timeout=60)


@register_tool(
    name="desktop_activate",
    description="激活指定窗口（按标题模糊匹配，自动恢复最小化并置前）。用于把微信/QQ/任意软件窗口切到前台。",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "窗口标题关键字（如 微信）"},
        },
        "required": ["title"],
    },
    category="desktop"
)
def desktop_activate(title: str) -> str:
    """激活窗口"""
    if not title.strip():
        return "请提供窗口标题关键字（--title）"
    return _run(['activate', '--title', title], timeout=30)


@register_tool(
    name="desktop_screenshot",
    description="对桌面全屏或指定区域截图保存到本地。用于查看当前屏幕状态、记录证据。",
    parameters={
        "type": "object",
        "properties": {
            "save": {"type": "string", "description": "保存路径（留空自动生成到 data/screenshots）", "default": ""},
            "region": {"type": "string", "description": "区域 x,y,w,h（留空=全屏）", "default": ""},
        },
        "required": [],
    },
    category="desktop"
)
def desktop_screenshot(save: str = "", region: str = "") -> str:
    """截图"""
    args = ['screenshot']
    if save:
        args += ['--save', save]
    if region:
        args += ['--region', region]
    return _run(args, timeout=30)


@register_tool(
    name="desktop_ocr",
    description="对屏幕（全屏或指定区域）进行 OCR 文字识别，返回每行文字的坐标。用于了解屏幕上有哪些按钮/文字、定位元素。engine 可选 smart（自适应：干净界面秒出，乱码界面自动双引擎融合）/auto（最快）/fusion（最准但慢，双引擎融合）/win/rapid。",
    parameters={
        "type": "object",
        "properties": {
            "region": {"type": "string", "description": "区域 x,y,w,h（留空=全屏）", "default": ""},
            "engine": {"type": "string", "description": "OCR引擎: smart/auto/fusion/win/rapid，默认 auto（最快）", "default": "auto"},
        },
        "required": [],
    },
    category="desktop"
)
def desktop_ocr(region: str = "", engine: str = "auto") -> str:
    """屏幕 OCR"""
    args = ['ocr']
    if region:
        args += ['--region', region]
    if engine and engine != 'auto':
        args += ['--engine', engine]
    return _run(args, timeout=120)


@register_tool(
    name="desktop_see",
    description="看懂屏幕（桌面视觉·快+准）：一次截图→本地画面分析（主色调/亮度/红绿告警块，毫秒级）+ OCR + 视觉大模型语义理解（GLM-4.6V）。已优化：①快：干净界面 OCR 秒出，一次截图全链路复用；②准：乱码界面自动切换双引擎融合(RapidOCR)，VLM 元素坐标已换算为真实屏幕像素可直接点击，JSON 容错解析；③VLM 输出画面摘要/元素列表/状态/警告/操作建议。比 desktop_ocr 更全面，能看懂「画面里有什么、按钮是否可用、有没有弹窗」；看不清/识别不出时优先用这个。engine 可选 smart（默认，自适应快+准）/auto（最快）/fusion（最准但慢）。",
    parameters={
        "type": "object",
        "properties": {
            "region": {"type": "string", "description": "区域 x,y,w,h（留空=全屏）", "default": ""},
            "save": {"type": "string", "description": "截图保存路径（留空自动保存到 data/screenshots）", "default": ""},
            "engine": {"type": "string", "description": "OCR引擎: smart(默认,自适应)/auto(最快)/fusion(最准但慢)/win/rapid", "default": "smart"},
            "vlm": {"type": "boolean", "description": "是否调用视觉大模型理解画面（默认 true；false 更快）", "default": True},
        },
        "required": [],
    },
    category="desktop"
)
def desktop_see(region: str = "", save: str = "", engine: str = "smart", vlm: bool = True) -> str:
    """看懂屏幕：一次截图 + 本地分析 + 自适应OCR +（可选）多模态视觉理解"""
    args = ['see']
    if region:
        args += ['--region', region]
    if save:
        args += ['--save', save]
    if engine and engine != 'smart':
        args += ['--engine', engine]
    if not vlm:
        args += ['--no-vlm']
    return _run(args, timeout=180)


@register_tool(
    name="desktop_uia",
    description="UI Automation 控件树：直接读取目标窗口的原生控件（按钮/输入框/文本/列表项），带控件类型/名称/坐标。比 OCR 快 10 倍且零乱码（不依赖图像识别）。适合：找微信发送按钮、输入框、菜单项等原生控件。优先 pywinauto，自动回退 uiautomation。",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "窗口标题关键字（留空=前台窗口）", "default": ""},
            "depth": {"type": "integer", "description": "遍历深度", "default": 4},
            "top": {"type": "integer", "description": "最多返回控件数", "default": 80},
        },
        "required": [],
    },
    category="desktop"
)
def desktop_uia(title: str = "", depth: int = 4, top: int = 80) -> str:
    """读取 UIA 控件树"""
    args = ['uia', '--depth', str(depth), '--top', str(top)]
    if title:
        args += ['--title', title]
    return _run(args, timeout=90)


@register_tool(
    name="desktop_tmatch",
    description="模板匹配：用图像模板（如发送/保存按钮图标、LOGO）在屏幕中定位元素，比 OCR 更稳（不依赖文字识别）。返回所有匹配点坐标+相似度。用法：先把目标图标截图存成 png（可用 desktop_screenshot 裁剪），再传入 --template 匹配。",
    parameters={
        "type": "object",
        "properties": {
            "template": {"type": "string", "description": "模板图片路径（如 data/screenshots/btn_send.png）"},
            "region": {"type": "string", "description": "限定搜索区域 x,y,w,h（留空=全屏）", "default": ""},
            "threshold": {"type": "number", "description": "匹配阈值 0~1，默认 0.8（越高越严格）", "default": 0.8},
            "max_matches": {"type": "integer", "description": "最多返回匹配数", "default": 5},
        },
        "required": ["template"],
    },
    category="desktop"
)
def desktop_tmatch(template: str, region: str = "", threshold: float = 0.8, max_matches: int = 5) -> str:
    """模板匹配定位"""
    if not template.strip():
        return "请提供模板图片路径（--template）"
    args = ['tmatch', '--template', template, '--threshold', str(threshold),
            '--max-matches', str(max_matches)]
    if region:
        args += ['--region', region]
    return _run(args, timeout=60)


@register_tool(
    name="desktop_click_text",
    description="按文字定位点击：OCR 找到屏幕上指定的文字（按钮/菜单项），点击其中心。文字支持 | 分隔多个候选。可传排除词防止点错。支持 --window 前置窗口验证：点前确认前台窗口是目标窗口，防止点错对象。",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要点击的文字（多个候选用 | 分隔，如 发表|发送）"},
            "exclude": {"type": "string", "description": "排除词（含这些词的文字不点，多个用 | 分隔）", "default": ""},
            "region": {"type": "string", "description": "限定搜索区域 x,y,w,h（留空=全屏）", "default": ""},
            "double": {"type": "boolean", "description": "是否双击", "default": False},
            "window": {"type": "string", "description": "点击前验证前台窗口标题含此关键字（如 微信），不符则拒绝点击（防误点）", "default": ""},
        },
        "required": ["text"],
    },
    category="desktop"
)
def desktop_click_text(text: str, exclude: str = "", region: str = "", double: bool = False, window: str = "") -> str:
    """按文字点击（含窗口验证）"""
    if not text.strip():
        return "请提供要点击的文字（--text）"
    args = ['click', '--text', text]
    if exclude:
        args += ['--exclude', exclude]
    if region:
        args += ['--region', region]
    if double:
        args += ['--double']
    if window:
        args += ['--window', window]
    return _run(args, timeout=60)


@register_tool(
    name="desktop_click_pos",
    description="按屏幕坐标点击（x,y）。适合已知精确位置时使用。",
    parameters={
        "type": "object",
        "properties": {
            "pos": {"type": "string", "description": "坐标 x,y（如 500,300）"},
            "double": {"type": "boolean", "description": "是否双击", "default": False},
        },
        "required": ["pos"],
    },
    category="desktop"
)
def desktop_click_pos(pos: str, double: bool = False) -> str:
    """坐标点击"""
    if not pos.strip():
        return "请提供坐标（--pos x,y）"
    args = ['click-pos', '--pos', pos]
    if double:
        args += ['--double']
    return _run(args, timeout=30)


@register_tool(
    name="desktop_type_text",
    description="向当前焦点输入文本：剪贴板直写+Ctrl+V 粘贴（毫秒级，支持中文）。可先点击指定坐标再输入。",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要输入的文本内容"},
            "pos": {"type": "string", "description": "先点击的坐标 x,y（可选）", "default": ""},
        },
        "required": ["text"],
    },
    category="desktop"
)
def desktop_type_text(text: str, pos: str = "") -> str:
    """输入文本"""
    if not text:
        return "请提供文本内容（--text）"
    args = ['type', '--text', text]
    if pos:
        args += ['--pos', pos]
    return _run(args, timeout=30)


@register_tool(
    name="desktop_paste_image",
    description="把本地图片粘贴到当前焦点窗口（剪贴板写入图片+Ctrl+V）。用于往聊天/编辑器里贴图。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "本地图片路径"},
            "pos": {"type": "string", "description": "先点击的坐标 x,y（可选）", "default": ""},
        },
        "required": ["path"],
    },
    category="desktop"
)
def desktop_paste_image(path: str, pos: str = "") -> str:
    """粘贴图片"""
    if not path:
        return "请提供图片路径（--path）"
    args = ['paste-img', '--path', path]
    if pos:
        args += ['--pos', pos]
    return _run(args, timeout=30)


@register_tool(
    name="desktop_hotkey",
    description="发送键盘组合键（如 ctrl,f / ctrl,v / alt,tab / enter）。用于触发搜索、粘贴、发送等操作。",
    parameters={
        "type": "object",
        "properties": {
            "keys": {"type": "string", "description": "组合键，逗号分隔（如 ctrl,f 或 enter）"},
        },
        "required": ["keys"],
    },
    category="desktop"
)
def desktop_hotkey(keys: str) -> str:
    """组合键"""
    if not keys.strip():
        return "请提供键位（--keys ctrl,f）"
    return _run(['hotkey', '--keys', keys], timeout=30)


@register_tool(
    name="desktop_verify",
    description="验证屏幕是否出现指定文字（OCR 全屏/区域查找）。用于操作后确认结果（消息上屏、弹窗出现等）。",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要查找的文字（多个候选用 | 分隔）"},
            "region": {"type": "string", "description": "限定区域 x,y,w,h（留空=全屏）", "default": ""},
        },
        "required": ["text"],
    },
    category="desktop"
)
def desktop_verify(text: str, region: str = "") -> str:
    """验证屏幕文字"""
    if not text.strip():
        return "请提供要查找的文字（--text）"
    args = ['verify', '--text', text]
    if region:
        args += ['--region', region]
    return _run(args, timeout=60)


@register_tool(
    name="desktop_send_chat",
    description="通用聊天发送流程：激活窗口 → 打开搜索(Ctrl+F) → 输入搜索词 → 回车进入聊天 → 粘贴消息 → 回车发送 → OCR 验证消息上屏。⚠️ 内置防发错闸门：回车进入聊天后，先 OCR 确认目标对象名称出现在屏幕上，确认不了就拒绝发送（杜绝发错对象）。用于微信/QQ等桌面聊天软件自动发消息。",
    parameters={
        "type": "object",
        "properties": {
            "window": {"type": "string", "description": "窗口标题关键字（如 微信）"},
            "search": {"type": "string", "description": "搜索对象名（如 7坛游戏社区）"},
            "message": {"type": "string", "description": "要发送的消息内容"},
            "hotkey": {"type": "string", "description": "搜索快捷键（默认 ctrl,f）", "default": "ctrl,f"},
        },
        "required": ["window", "search", "message"],
    },
    category="desktop"
)
def desktop_send_chat(window: str, search: str, message: str, hotkey: str = "ctrl,f") -> str:
    """通用聊天发送"""
    if not window.strip() or not search.strip() or not message.strip():
        return "请提供 window/search/message 三项参数"
    return _run(['send-chat', '--window', window, '--search', search,
                 '--message', message, '--hotkey', hotkey], timeout=90)
