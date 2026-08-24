# -*- coding: utf-8 -*-
"""
公众号排版渲染插件 — 一键生成"可直接复制到公众号"的排版 HTML
解决痛点：公众号编辑器不认复杂 CSS（圆角/阴影/flex），复制过去会变形。
本插件只输出公众号能识别的基础样式：背景色高亮、加粗、颜色、引用块、分割线，
保证"选中渲染内容复制粘贴到公众号"后，高亮/加粗/引用 100% 保留。

工具:
  gzh_render  把轻量 Markdown 正文渲染成公众号排版 HTML（本地预览 + 存档）

Markdown 语法（AI 生成内容时按此写）:
  ## 小标题           → 加粗大字
  >  引用文字         → 浅灰底引用块
  >> 金句             → 黄色高亮 + 加粗 + 居中
  ---                 → 分割线
  ![图注](图片路径)    → 居中图片 + 图注
  @@ 互动内容         → 浅蓝底互动框（引导评论）
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

BASE_CSS = """
body{margin:0 auto;padding:24px 20px;max-width:640px;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:16px;line-height:1.75;color:#333333;background:#ffffff;}
.article-title{font-size:21px;font-weight:bold;text-align:center;color:#1a1a1a;margin:0 0 10px;line-height:1.4;}
.article-subtitle{font-size:14px;color:#888888;text-align:center;margin:0 0 18px;}
.notice{font-size:13px;color:#999999;font-style:italic;background-color:#f5f5f5;padding:10px 14px;margin:16px 0;text-align:center;}
p{margin:0 0 18px;}
h2{font-size:18px;font-weight:bold;color:#1a1a1a;margin:28px 0 14px;}
.quote{background-color:#fdf6e3;color:#8a5a00;font-weight:bold;padding:14px 16px;margin:20px 0;text-align:center;font-size:16px;}
blockquote{background-color:#f5f5f5;color:#555555;padding:12px 16px;margin:20px 0;}
figure{margin:20px 0;text-align:center;}
figure img{max-width:100%;display:block;margin:0 auto;}
figcaption{font-size:13px;color:#999999;margin-top:8px;text-align:center;}
hr{border:none;border-top:1px solid #e5e5e5;margin:24px 0;}
.interact{background-color:#f0f7ff;padding:14px 16px;margin:20px 0;font-size:15px;}
.cta{text-align:center;color:#d33c3c;font-weight:bold;margin:20px 0;}
.hl{background-color:#fff3b0;padding:0 2px;}
"""


def _escape(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _inline(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'==(.+?)==', r'<span class="hl">\1</span>', text)
    return text


def _render_body(content: str) -> str:
    out = []
    for line in content.split('\n'):
        s = line.rstrip()
        if not s.strip():
            continue
        if s.startswith('## '):
            out.append('<h2>%s</h2>' % _inline(_escape(s[3:].strip())))
        elif s.startswith('>> '):
            out.append('<p class="quote">%s</p>' % _inline(_escape(s[3:].strip())))
        elif s.startswith('> '):
            out.append('<blockquote>%s</blockquote>' % _inline(_escape(s[2:].strip())))
        elif s.strip() == '---':
            out.append('<hr>')
        elif s.startswith('@@ '):
            out.append('<div class="interact">%s</div>' % _inline(_escape(s[3:].strip())))
        elif s.startswith('!! '):
            out.append('<p class="cta">%s</p>' % _inline(_escape(s[3:].strip())))
        elif s.startswith('!['):
            m = re.match(r'!\[(.*?)\]\((.*?)\)', s)
            if m:
                cap, src = m.group(1), m.group(2)
                out.append('<figure><img src="%s" alt="%s"><figcaption>%s</figcaption></figure>'
                           % (_escape(src), _escape(cap), _escape(cap)))
        else:
            out.append('<p>%s</p>' % _inline(_escape(s.strip())))
    return '\n'.join(out)


@register_tool(
    name="gzh_render",
    description="把轻量Markdown正文渲染成公众号排版HTML（本地预览+存档）。生成内容只含公众号能识别的样式（背景高亮/加粗/颜色/引用块/分割线），复制粘贴到公众号编辑器不会变形。Markdown语法：##小标题、>引用、>>金句、---分割线、![图注](图片路径)图片、@@互动框、!!CTA、**加粗**、==高亮==。",
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
    """渲染公众号排版 HTML"""
    try:
        body = _render_body(content)
        subtitle_html = ('<div class="article-subtitle">%s</div>' % _inline(_escape(subtitle))) if subtitle.strip() else ''
        notice_html = ('<div class="notice">%s</div>' % _inline(_escape(notice))) if notice.strip() else ''

        html = ('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
                '<meta charset="UTF-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
                '<title>%s</title>\n<style>%s</style>\n</head>\n<body>\n'
                '<h1 class="article-title">%s</h1>\n%s\n%s\n%s\n</body>\n</html>'
                % (_escape(title), BASE_CSS, _escape(title), subtitle_html, notice_html, body))

        if not output_path.strip():
            safe = re.sub(r'[\\/:*?"<>|]', '_', title)[:40]
            output_path = str(ROOT / 'data' / 'gzh_render' / (safe + '.html'))
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html, encoding='utf-8')

        char_count = len(re.sub(r'\s', '', content))
        img_count = content.count('![')
        return ('✅ 公众号排版 HTML 已生成！\n'
                '📄 文件: %s\n'
                '📏 正文字数: %d 字\n'
                '🖼️ 图片: %d 张\n\n'
                '💡 使用：浏览器打开预览 → 选中正文 Ctrl+C → 公众号编辑器 Ctrl+V，'
                '高亮/加粗/引用自动保留；图片需在公众号后台手动上传。'
                % (p, char_count, img_count))
    except Exception as e:
        return '❌ 渲染失败: %s' % e
