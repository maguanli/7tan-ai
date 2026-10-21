"""
最小化 HTML 改写（byte-preserving）。

背景
----
早期实现用 ``str(BeautifulSoup(html))`` 输出，而 BeautifulSoup 的序列化会
**按自己的规则重排整个文档**：

  * 重排标签属性顺序（例如 ``name``/``content`` 被对调，实际是隐式排序）；
  * 给 ``<meta>`` ``<link>`` ``<br>`` ``<img>`` 等 void 元素补自闭合斜杠 ``/>``；
  * 统一引号风格、转义实体、重排空白。

结果就是"镜像下来的代码和原站不一样"，违背了"原样复制"的目标。

本模块改用**定位式改写**：借 ``html.parser.HTMLParser`` 拿到每个标签在原文
中的精确偏移，只在原文上替换真正需要改动的字节（链接属性值、字符集声明），
其余字节——属性顺序、引号、空白、注释、``<script>`` 内容——一律保持原样。

对外只暴露一个函数 :func:`rewrite_html`。
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

# 属性名 -> 预编译正则（匹配 "attr=值" 中的值部分）
_ATTR_RE_CACHE: dict[str, re.Pattern] = {}
# charset=xxx（用于改写 <meta http-equiv=content-type content="...; charset=x">）
_CHARSET_EQ_RE = re.compile(r"charset\s*=\s*[\w\-]+", re.I)


def _attr_re(attr: str) -> re.Pattern:
    """取（并缓存）匹配 ``attr=值`` 的正则；兼容带引号与不带引号两种写法。"""
    pat = _ATTR_RE_CACHE.get(attr)
    if pat is None:
        pat = re.compile(
            r"(?i)(?<![\w:\-])(" + re.escape(attr) + r"\s*=\s*)"
            r"(?:([\"'])(.*?)\2|([^\s\"'>`=]+))",
            re.S,
        )
        _ATTR_RE_CACHE[attr] = pat
    return pat


def _escape_attr_value(v: str) -> str:
    """属性值里最少的转义：& 与双引号。"""
    return v.replace("&", "&amp;").replace('"', "&quot;")


def _replace_attr(seg: str, attr: str, new_value: str) -> str:
    """把标签片段 ``seg`` 中 ``attr`` 的值替换为 ``new_value``（只替换第一处）。

    带引号的值沿用原引号风格；不带引号的值在安全时继续保持不带引号。
    """
    def repl(m: re.Match) -> str:
        prefix = m.group(1)
        if m.group(2):                                   # 原文带引号
            q = m.group(2)
            return prefix + q + _escape_attr_value(new_value) + q
        if re.search(r"[\s\"'`=<>]", new_value):        # 有特殊字符，必须加引号
            return prefix + '"' + _escape_attr_value(new_value) + '"'
        return prefix + new_value

    return _attr_re(attr).sub(repl, seg, count=1)


class _Scanner(HTMLParser):
    """扫描原文，记录标签位置与 style 块内容区间（不做任何改写）。"""

    def __init__(self, html: str):
        super().__init__(convert_charrefs=False)
        self.html = html
        self.tags: list[tuple[str, list, int, int]] = []   # (tag, attrs, start, end)
        self.style_blocks: list[tuple[int, int]] = []      # <style> 内容 [start, end)
        starts = [0]
        for ln in html.splitlines(keepends=True):
            starts.append(starts[-1] + len(ln))
        self._line_starts = starts
        self._style_open: int | None = None

    # --- 位置换算 ---
    def _offset(self, pos) -> int:
        line, col = pos
        if line - 1 < len(self._line_starts):
            return self._line_starts[line - 1] + col
        return len(self.html)

    def _find_end(self, start: int) -> int:
        """从标签起始 ``<`` 找到配对的 ``>``（考虑引号内不闭合）。"""
        i, quote, n = start, None, len(self.html)
        while i < n:
            c = self.html[i]
            if quote is not None:
                if c == quote:
                    quote = None
            elif c in "\"'":
                quote = c
            elif c == ">":
                return i
            i += 1
        return n - 1

    # --- HTMLParser 回调 ---
    def handle_starttag(self, tag, attrs):
        start = self._offset(self.getpos())
        end = self._find_end(start)
        self.tags.append((tag, attrs, start, end))
        if tag == "style":
            self._style_open = min(end + 1, len(self.html))

    def handle_startendtag(self, tag, attrs):
        start = self._offset(self.getpos())
        end = self._find_end(start)
        self.tags.append((tag, attrs, start, end))

    def handle_endtag(self, tag):
        if tag == "style" and self._style_open is not None:
            self.style_blocks.append((self._style_open, self._offset(self.getpos())))
            self._style_open = None


def _normalize_meta_charset(seg: str, attrs: list) -> str:
    """把 <meta> 的字符集声明改写成 utf-8（仅当该 meta 确实带声明时）。"""
    d = {k.lower(): (v or "") for k, v in attrs if k}
    if "charset" in d:
        return _replace_attr(seg, "charset", "utf-8")
    if d.get("http-equiv", "").lower() == "content-type" and "charset" in d.get("content", "").lower():
        new_content = _CHARSET_EQ_RE.sub("charset=utf-8", d["content"])
        return _replace_attr(seg, "content", new_content)
    return seg


def _has_charset_decl(tags: list) -> bool:
    """判断文档里是否已存在字符集声明。"""
    for tag, attrs, _s, _e in tags:
        if tag != "meta":
            continue
        d = {k.lower(): (v or "") for k, v in attrs if k}
        if "charset" in d:
            return True
        if d.get("http-equiv", "").lower() == "content-type" and \
                "charset" in d.get("content", "").lower():
            return True
    return False


def rewrite_html(html: str, attr_map=None, style_map=None, *,
                 ensure_charset: bool = True) -> str:
    """
    在原文上做最小化改写。

    :param html: 原始 HTML 文本
    :param attr_map: ``attr_map(tag, attr, value, attrs) -> str | None``；
                     返回新值则替换该属性值，返回 None 则保持原样。
                     ``attrs`` 为该标签的全部属性 dict（便于判断 rel 等）。
    :param style_map: ``style_map(css_text) -> str``，处理 ``<style>`` 块与
                      内联 ``style`` 属性里的 CSS。
    :param ensure_charset: 若文档完全没有字符集声明，则在 ``<head>`` 后补一条
                      ``<meta charset="utf-8">``（镜像按 UTF-8 落盘，缺声明会乱码）。
    :return: 改写后的 HTML（未触及的字节与原文完全一致）
    """
    sc = _Scanner(html)
    try:
        sc.feed(html)
        sc.close()
    except Exception:                       # noqa: BLE001  解析失败就原样返回
        return html

    edits: list[tuple[int, int, str]] = []  # (start, end, 替换文本)
    head_insert_at: int | None = None

    # 1) 标签级改写
    for tag, attrs, start, end in sc.tags:
        seg = html[start:end + 1]
        new_seg = seg

        if tag == "meta" and ensure_charset:
            new_seg = _normalize_meta_charset(new_seg, attrs)

        if attr_map:
            attrs_dict = {k.lower(): (v or "") for k, v in attrs if k}
            for a, v in attrs:
                if not a or v is None:
                    continue
                try:
                    nv = attr_map(tag, a, v, attrs_dict)
                except Exception:           # noqa: BLE001  单个属性失败不影响整体
                    nv = None
                if nv is not None and nv != v:
                    new_seg = _replace_attr(new_seg, a, nv)

        if style_map:
            for a, v in attrs:
                if a == "style" and v and "url(" in v.lower():
                    try:
                        nv = style_map(v)
                    except Exception:       # noqa: BLE001
                        nv = None
                    if nv:
                        new_seg = _replace_attr(new_seg, "style", nv)

        if new_seg != seg:
            edits.append((start, end + 1, new_seg))

        if tag == "head" and head_insert_at is None:
            head_insert_at = end + 1

    # 2) <style> 块内容
    if style_map:
        for s, e in sc.style_blocks:
            css = html[s:e]
            if not css:
                continue
            try:
                nc = style_map(css)
            except Exception:               # noqa: BLE001
                nc = None
            if nc and nc != css:
                edits.append((s, e, nc))

    # 3) 缺 charset 声明则补一条
    if ensure_charset and not _has_charset_decl(sc.tags):
        at = head_insert_at if head_insert_at is not None else 0
        edits.append((at, at, '<meta charset="utf-8"/>'))

    if not edits:
        return html

    # 从后往前应用，避免偏移互相影响
    edits.sort(key=lambda x: x[0])
    out: list[str] = []
    pos = 0
    for s, e, txt in edits:
        if s < pos:                          # 与前一处重叠，跳过（不应发生）
            continue
        out.append(html[pos:s])
        out.append(txt)
        pos = e
    out.append(html[pos:])
    return "".join(out)
