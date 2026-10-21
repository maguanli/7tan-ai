"""
URL → 本地文件路径映射（镜像保存的核心）。

设计目标：**严格按原站 URL 的目录结构原样落地**，保证不同 URL 一一对应、互不覆盖。

映射示例（默认参数）：
    https://example.com/                    ->  example.com/index.html
    https://example.com/index.html          ->  example.com/index.html
    https://example.com/docs/guide.html     ->  example.com/docs/guide.html
    https://example.com/docs/               ->  example.com/docs/index.html
    https://example.com/about               ->  example.com/about/index.html   (无扩展名=目录)
    https://example.com/img/logo.png        ->  example.com/img/logo.png
    https://example.com/list?page=2         ->  example.com/list/@page=2/index.html
    https://example.com/i.php?id=9          ->  example.com/i@id=9.php
    https://example.com/a/b?x=1&y=2         ->  example.com/a/b/@x=1@y=2/index.html
    http://example.com:8080/                ->  example.com_8080/index.html

参数：
    param_mode    query 处理方式：dir(默认,转目录名) / hash(取哈希) / ignore(丢弃)
    extensionless 无扩展名路径落地方式：index(默认,<name>/index.html) / html(<name>.html)
    with_host     是否在顶层加域名目录（默认 True，多站抓取时避免冲突）
    case_safe_paths 大小写折叠冲突路径集合（小写 relpath）；命中则附加 URL 短哈希，
                  规避 Windows 大小写不敏感导致的互相覆盖
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import unquote, unquote_plus, urlsplit

# Windows 非法字符 + 控制字符
_ILLEGAL = set('<>:"/\\|?*')
# Windows 保留设备名
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# 资源扩展名 -> 常见类型
HTML_EXT = {".html", ".htm", ".xhtml", ".shtml"}
CSS_EXT = {".css"}
_EXT_RE = re.compile(r"^(.*?)(\.[A-Za-z0-9]{1,8})$")
_SAFE_MAX = 240  # 总相对路径最大长度


def split_ext(name: str) -> tuple[str, str]:
    """拆分文件名与扩展名：('i.php', '.php') / ('about', '')"""
    m = _EXT_RE.match(name)
    if m:
        return m.group(1), m.group(2).lower()
    return name, ""


def sanitize_segment(seg: str, max_len: int = 100) -> str:
    """把 URL 路径段净化为安全文件名（保留中文，剔除非法字符）。"""
    seg = unquote(seg)
    seg = seg.replace("\x00", "")
    buf = []
    for ch in seg:
        if ch in _ILLEGAL or ord(ch) < 32:
            buf.append("_")
        else:
            buf.append(ch)
    s = "".join(buf).strip()            # Windows 不允许首尾空格
    if s in (".", ".."):                # 防目录穿越：. / .. 一律改名
        return "__" if s == ".." else "_"
    s = s.rstrip(".")                   # Windows 不允许结尾的点
    if not s:
        s = "_"
    if s.upper().split(".")[0] in _RESERVED:
        s = "_" + s
    if len(s) > max_len:               # 超长则截断 + 短哈希防冲突
        s = s[:max_len] + "_" + hashlib.md5(seg.encode("utf-8")).hexdigest()[:8]
    return s


def _query_segment(query: str, param_mode: str = "dir") -> str | None:
    """把 query 转成路径段。返回 None 表示丢弃 query。"""
    if not query:
        return ""
    if param_mode == "ignore":
        return None
    if param_mode == "hash":
        return "@q=" + hashlib.md5(query.encode("utf-8")).hexdigest()[:10]
    parts = []
    for kv in query.split("&"):
        if not kv:
            continue
        k, _, v = kv.partition("=")
        k, v = unquote_plus(k), unquote_plus(v)
        if len(v) > 60:  # 超长参数值（如 base64）折叠
            v = v[:40] + "_" + hashlib.md5(v.encode("utf-8")).hexdigest()[:8]
        raw = f"{k}={v}" if k else v
        parts.append(sanitize_segment(raw, max_len=80))
    if not parts:
        return None
    return "@" + "@".join(parts)


def _fold(relpath: str, max_len: int = _SAFE_MAX) -> str:
    """路径过长时折叠中间目录为哈希，保证不超文件系统限制。"""
    if len(relpath) <= max_len:
        return relpath
    parts = relpath.split("/")
    head, tail = parts[0], parts[-1]
    digest = hashlib.md5(relpath.encode("utf-8")).hexdigest()[:12]
    mid = [f"_{digest}"]
    out = [head] + mid + [tail]
    return "/".join(out)


def url_to_relpath(
    url: str,
    *,
    param_mode: str = "dir",
    extensionless: str = "index",
    with_host: bool = True,
    host_dir_map: dict | None = None,
    case_safe_paths: set | None = None,
) -> str:
    """把 URL 映射成任务目录内的相对路径（POSIX 风格，用 / 分隔）。"""
    sp = urlsplit(url)
    host = sp.hostname or "unknown"
    if sp.port and sp.port not in (80, 443):
        host = f"{host}_{sp.port}"

    path = sp.path or "/"
    is_dir = path.endswith("/") or path in ("", "/")

    parts: list[str] = []
    if with_host:
        # host_dir_map 允许把某些域名落到别的顶层目录（如 {"a.com": "a.com2"}）：
        # 只改本地落盘位置，不改变 URL 解析与去重（去重按 URL，见 crawler._restore_state）。
        parts.append(sanitize_segment((host_dir_map or {}).get(host, host), 80))

    raw_segs = [s for s in path.split("/") if s]
    segs = [sanitize_segment(s) for s in raw_segs]

    qseg = _query_segment(sp.query, param_mode)
    has_query = qseg not in (None, "")

    parts.extend(segs)

    if not parts:                      # 极端情况：with_host=False 且 path=/）
        parts.append("index")

    if is_dir:
        if has_query:
            parts.append(qseg)
        parts.append("index.html")
    else:
        last = parts[-1]
        name, ext = split_ext(last)
        if ext:
            parts[-1] = f"{name}{qseg}{ext}" if has_query else last
        else:
            if extensionless == "index":
                if has_query:
                    parts.append(qseg)
                parts.append("index.html")
            else:
                parts[-1] = f"{name}{qseg}.html" if has_query else f"{name}.html"

    rel = _fold("/".join(parts))
    # 大小写安全：若该路径（忽略大小写）会与其他 URL 相撞（Windows 文件系统
    # 大小写不敏感，后写入的会覆盖先写入的），则在扩展名前插入该 URL 的短哈希，
    # 保证不同页面各自落盘、互不覆盖。
    if case_safe_paths and rel.lower() in case_safe_paths:
        head, sep, tail = rel.rpartition("/")
        name, ext = split_ext(tail)
        digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        tail = f"{name}-{digest}{ext}"
        rel = f"{head}{sep}{tail}" if sep else tail
    return rel


def relpath_to_url_path(relpath: str) -> str:
    """反解：本地相对路径 -> 近似原始 URL 路径（用于展示）。"""
    return "/" + relpath.replace("\\", "/")


def guess_ext_by_content_type(ctype: str) -> str:
    """根据 Content-Type 猜测扩展名（缺扩展名资源落盘时用）。"""
    ctype = (ctype or "").split(";")[0].strip().lower()
    table = {
        "text/html": ".html", "application/xhtml+xml": ".html",
        "text/css": ".css", "text/plain": ".txt", "text/xml": ".xml",
        "application/xml": ".xml", "application/json": ".json",
        "application/javascript": ".js", "text/javascript": ".js",
        "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
        "image/webp": ".webp", "image/svg+xml": ".svg", "image/x-icon": ".ico",
        "image/avif": ".avif", "image/bmp": ".bmp",
        "font/woff": ".woff", "font/woff2": ".woff2", "font/ttf": ".ttf",
        "font/otf": ".otf", "application/font-woff": ".woff",
        "application/pdf": ".pdf", "video/mp4": ".mp4", "audio/mpeg": ".mp3",
        "application/zip": ".zip", "application/wasm": ".wasm",
    }
    return table.get(ctype, "")


def is_html_path(relpath: str) -> bool:
    return split_ext(relpath)[1] in HTML_EXT


def is_css_path(relpath: str) -> bool:
    return split_ext(relpath)[1] in CSS_EXT
