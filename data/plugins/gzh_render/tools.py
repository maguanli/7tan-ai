# -*- coding: utf-8 -*-
"""
公众号排版渲染插件 v1.1 —「90%%兼容版」
升级点：所有排版样式全部写成【内联 style 属性】，公众号编辑器粘贴时按内联样式保留，
不再依赖 <style> 类样式（类样式粘贴会丢）。

兼容性设计（公众号编辑器可保留的 CSS 子集）：
  ✅ 保留：背景色 background-color、文字颜色 color、加粗、斜体、居中、
           内边距 padding、圆角 border-radius、实线边框 border、分割线
  ❌ 不用：flex/grid 布局、box-shadow 阴影、渐变、伪元素、动画 —— 粘贴必丢
所以：浏览器预览效果 ≈ 粘贴到公众号后的效果，90%+ 样式保留。

工具:
  gzh_render  把轻量 Markdown 正文渲染成公众号排版 HTML（本地预览 + 存档）

Markdown 语法（AI 生成内容时按此写）:
  ## 小标题           → 加粗大字 + 金色竖线
  >  引用文字         → 浅灰底引用块（带竖线）
  >> 金句             → 黄色高亮 + 加粗 + 居中 + 圆角卡
  ---                 → 分割线
  ![图注](图片路径)    → 居中图片（圆角）+ 图注
  @@ 互动内容         → 浅蓝底互动框（引导评论，圆角）
  !! CTA文字          → 红色加粗居中（引导在看/转发）
  **加粗** / ==高亮==  → 行内加粗 / 行内黄色高亮
  普通段落直接写
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

# ---------- 内联样式常量（公众号可保留的 CSS 子集） ----------
S_TITLE    = 'font-size:22px;font-weight:bold;text-align:center;color:#1a1a1a;margin:0 0 10px;line-height:1.5;'
S_SUBTITLE = 'font-size:14px;color:#999999;text-align:center;margin:0 0 18px;'
S_NOTICE   = 'font-size:13px;color:#888888;font-style:italic;background-color:#f7f7f7;padding:10px 14px;margin:16px 0;text-align:center;border-left:3px solid #dddddd;'
S_P        = 'margin:0 0 18px;font-size:16px;line-height:1.8;color:#333333;'
S_H2       = 'font-size:18px;font-weight:bold;color:#8a5a00;margin:28px 0 14px;padding-left:10px;border-left:4px solid #e8b84b;'
S_QUOTE    = 'background-color:#fff8e1;color:#8a5a00;font-weight:bold;padding:16px 18px;margin:20px 0;text-align:center;font-size:17px;border-radius:8px;'
S_BQ       = 'background-color:#f5f5f5;color:#555555;padding:12px 16px;margin:20px 0;border-left:4px solid #cccccc;font-size:15px;'
S_FIGURE   = 'margin:20px 0;text-align:center;'
S_IMG      = 'max-width:100%;display:block;margin:0 auto;border-radius:8px;'
S_FIGCAP   = 'font-size:13px;color:#999999;margin-top:8px;text-align:center;'
S_HR       = 'border:none;border-top:1px solid #e5e5e5;margin:24px 0;'
S_INTERACT = 'background-color:#f0f7ff;padding:14px 16px;margin:20px 0;font-size:15px;border-radius:8px;color:#3a6ea5;'
S_CTA      = 'text-align:center;color:#d33c3c;font-weight:bold;margin:20px 0;font-size:16px;'
S_HL       = 'background-color:#fff3b0;padding:0 2px;'

# 本地预览最小样式（与内联一致，所见即所得，无花哨 CSS）
PREVIEW_CSS = (
    'body{margin:0 auto;padding:24px 20px;max-width:640px;'
    "font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;"
    'background:#ffffff;}'
)


def _escape(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _inline(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'==(.+?)==', r'<span style="%s">\1</span>' % S_HL, text)
    return text


def _render_body(content: str) -> str:
    out = []
    for line in content.split('\n'):
        s = line.rstrip()
        if not s.strip():
            continue
        if s.startswith('## '):
            out.append('<h2 style="%s">%s</h2>' % (S_H2, _inline(_escape(s[3:].strip()))))
        elif s.startswith('>> '):
            out.append('<p style="%s">%s</p>' % (S_QUOTE, _inline(_escape(s[3:].strip()))))
        elif s.startswith('> '):
            out.append('<blockquote style="%s">%s</blockquote>' % (S_BQ, _inline(_escape(s[2:].strip()))))
        elif s.strip() == '---':
            out.append('<hr style="%s">' % S_HR)
        elif s.startswith('@@ '):
            out.append('<div style="%s">%s</div>' % (S_INTERACT, _inline(_escape(s[3:].strip()))))
        elif s.startswith('!! '):
            out.append('<p style="%s">%s</p>' % (S_CTA, _inline(_escape(s[3:].strip()))))
        elif s.startswith('!['):
            m = re.match(r'!\[(.*?)\]\((.*?)\)', s)
            if m:
                cap, src = m.group(1), m.group(2)
                out.append('<figure style="%s"><img src="%s" alt="%s" style="%s"><figcaption style="%s">%s</figcaption></figure>'
                           % (S_FIGURE, _escape(src), _escape(cap), S_IMG, S_FIGCAP, _escape(cap)))
        else:
            out.append('<p style="%s">%s</p>' % (S_P, _inline(_escape(s.strip()))))
    return '\n'.join(out)


@register_tool(
    name="gzh_render",
    description="把轻量Markdown正文渲染成公众号排版HTML（本地预览+存档）。v1.1全部样式内联化，90%+排版（高亮/加粗/颜色/圆角卡/引用块/分割线/图注）复制粘贴到公众号编辑器可保留。Markdown语法：##小标题、>引用、>>金句、---分割线、![图注](图片路径)图片、@@互动框、!!CTA、**加粗**、==高亮==。",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "文章主标题"},
            "content": {"type": "string", "description": "正文内容（轻量Markdown，语法见description）"},
            "subtitle": {"type": "string", "description": "副标题/导语（可选）", "default": ""},
            "notice": {"type": "string", "description": "开头声明文字（可选）", "default": ""},
            "output_path": {"type": "string", "description": "输出HTML路径（可选，默认 data/gzh_render/标题.html）", "default": ""},
        },
        "required": ["title", "content"],
    },
    category="gzh_render",
)
def gzh_render(title: str, content: str, subtitle: str = "", notice: str = "",
               output_path: str = "") -> str:
    """渲染公众号排版 HTML（内联样式 · 90%%兼容版）"""
    try:
        body = _render_body(content)
        subtitle_html = ('<div style="%s">%s</div>' % (S_SUBTITLE, _inline(_escape(subtitle)))) if subtitle.strip() else ''
        notice_html = ('<div style="%s">%s</div>' % (S_NOTICE, _inline(_escape(notice)))) if notice.strip() else ''

        html = ('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
                '<meta charset="UTF-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
                '<title>%s</title>\n<style>%s</style>\n</head>\n<body>\n'
                '<h1 style="%s">%s</h1>\n%s\n%s\n%s\n</body>\n</html>'
                % (_escape(title), PREVIEW_CSS, S_TITLE, _escape(title), subtitle_html, notice_html, body))

        if not output_path.strip():
            safe = re.sub(r'[\\/:*?"<>|]', '_', title)[:40]
            output_path = str(ROOT / 'data' / 'gzh_render' / (safe + '.html'))
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html, encoding='utf-8')

        char_count = len(re.sub(r'\s', '', content))
        img_count = content.count('![')
        return ('✅ 公众号排版 HTML 已生成（v1.1 内联样式 · 90%%兼容版）！\n'
                '📄 文件: %s\n'
                '📏 正文字数: %d 字\n'
                '🖼️ 图片: %d 张\n\n'
                '💡 使用：浏览器打开预览 → 选中正文 Ctrl+C → 公众号编辑器 Ctrl+V，\n'
                '高亮/加粗/颜色/圆角卡/引用块/分割线/图注 90%%+ 自动保留；图片需在公众号后台手动上传。'
                % (p, char_count, img_count))
    except Exception as e:
        return '❌ 渲染失败: %s' % e
