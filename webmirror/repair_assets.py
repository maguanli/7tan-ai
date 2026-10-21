"""就地补抓缺失的静态资源（无需重新抓取整站）。

背景：早期版本把「同站」判定为「同主机」，导致托管在兄弟域名的
CSS/JS/图片（如 quhao.293.net 的样式托管在 i.293.net）被整站跳过，
已抓下来的页面因此没有样式。

本脚本对**已存在的镜像目录**做修复：
  1. 扫描所有 .html，找出仍指向外部主机的 CSS/JS/图片等资源；
  2. 按 URL → 本地路径 规则下载缺失文件（保持原路径）；
  3. 把 HTML / CSS 里的引用改写成本地相对路径（与原工具一致）；
  4. 递归处理下载到的 CSS 内的 url() / @import。

用法：
    python repair_assets.py <任务目录> [--scope same_site|any|same_host] [--dry-run]
    python repair_assets.py downloads/20261011-061903-338184 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import posixpath
import re
import sys
from urllib.parse import urljoin, urlsplit

import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.crawler import DEFAULT_UA, base_domain            # noqa: E402
from app.paths import is_css_path, url_to_relpath          # noqa: E402

# 指向静态资源的 标签/属性（对应 crawler.LINK_ATTRS，排除页面链接）
ASSET_ATTRS: dict[str, set[str]] = {
    "link": {"href"}, "script": {"src"}, "img": {"src", "data-src", "srcset"},
    "source": {"src", "srcset"}, "video": {"src", "poster"}, "audio": {"src"},
    "embed": {"src"}, "object": {"data"}, "track": {"src"}, "input": {"src"},
}
PAGE_LINK_RELS = ("canonical", "alternate")
# 这些 rel 只是「主机提示」，不是资源文件，改写会破坏语义
SKIP_LINK_RELS = ("dns-prefetch", "preconnect")

SKIP_SCHEMES = ("javascript:", "mailto:", "tel:", "data:", "blob:", "about:",
                "sms:", "ftp:", "#")

TAG_RE = re.compile(r"""<(?P<tag>link|script|img|source|video|audio|embed|object|track|input)\b(?P<attrs>[^>]*)>""", re.I)
ATTR_RE = re.compile(r"""(?P<name>[\w:-]+)\s*=\s*(?P<q>["'])(?P<val>.*?)(?P=q)""", re.S)
CSS_URL_RE = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""", re.I)
CSS_IMPORT_RE = re.compile(r"""@import\s+(['"])([^'"]+)\1""", re.I)
HTML_EXTS = (".html", ".htm", ".shtml", ".xhtml")


def load_page_url_map(task_dir: str) -> dict[str, str]:
    """本地相对路径 -> 原始 URL（来自 _mirror_manifest.json）。"""
    mf = os.path.join(task_dir, "_mirror_manifest.json")
    mapping: dict[str, str] = {}
    if os.path.isfile(mf):
        with open(mf, encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("files", []) if isinstance(data, dict) else data
        for item in items:
            if not isinstance(item, dict):
                continue
            p, u = item.get("path"), item.get("url")
            if p and u:
                mapping.setdefault(p.replace("\\", "/"), u)
    return mapping


def manifest_start_url(task_dir: str) -> str:
    """任务目录的起始 URL（优先 _tasks.json，其次 _mirror_manifest.json）。"""
    idx = os.path.join(os.path.dirname(os.path.abspath(task_dir.rstrip("/\\"))), "_tasks.json")
    target = os.path.abspath(task_dir)
    if os.path.isfile(idx):
        try:
            with open(idx, encoding="utf-8") as f:
                for t in json.load(f):
                    if os.path.abspath(t.get("out_root", "")) == target:
                        u = t.get("config", {}).get("start_url") or t.get("start_url")
                        if u:
                            return u
        except Exception:                       # noqa: BLE001
            pass
    mf = os.path.join(task_dir, "_mirror_manifest.json")
    if os.path.isfile(mf):
        try:
            with open(mf, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("start_url"):
                return data["start_url"]
        except Exception:                       # noqa: BLE001
            pass
    return ""


def start_host(task_dir: str) -> str:
    """从 downloads/_tasks.json 找到该任务目录的起始主机。"""
    u = manifest_start_url(task_dir)
    if u:
        host = urlsplit(u).hostname
        if host:
            return host.lower()
    counts = {}
    for name in os.listdir(task_dir):
        if os.path.isdir(os.path.join(task_dir, name)) and "." in name:
            counts[name.lower()] = sum(1 for _ in os.scandir(os.path.join(task_dir, name)))
    return max(counts, key=counts.get) if counts else ""


class Repairer:
    def __init__(self, task_dir: str, scope: str, dry_run: bool, concurrency: int = 8):
        self.root = task_dir
        self.scope = scope
        self.dry_run = dry_run
        self.host = start_host(task_dir)
        self.url_of = load_page_url_map(task_dir)
        self.todo: dict[str, str] = {}          # 本地相对路径 -> URL
        self.downloaded = 0
        self.failed: list[dict] = []
        self.edited_html = 0
        self.css_edited = 0
        self.candidates = 0
        self.concurrency = concurrency
        self.start_url = manifest_start_url(task_dir)

    # ---------- 范围 / 路径 ----------
    def allowed(self, url: str) -> bool:
        sp = urlsplit(url)
        if sp.scheme not in ("http", "https"):
            return False
        host = (sp.hostname or "").lower()
        if self.scope == "any":
            return True
        if self.scope == "same_site":
            return base_domain(host) == base_domain(self.host)
        return host == self.host

    def local_path(self, url: str) -> str:
        return url_to_relpath(url, param_mode="dir", extensionless="index", with_host=True)

    def abs_path(self, rel: str) -> str:
        return os.path.join(self.root, *rel.split("/"))

    def exists(self, rel: str) -> bool:
        return os.path.isfile(self.abs_path(rel))

    # ---------- 核心：改写一条链接 ----------
    def rewrite_link(self, raw: str, page_url: str, cur_dir: str,
                     allow_relative: bool = False) -> str | None:
        """把一个仍指向外部的资源链接改写成本地相对路径；返回 None=不动。

        allow_relative：处理 CSS 内的相对 url() 时置 True。
        相对路径要按「CSS 文件自身所在 URL」解析——它可能落在兄弟域名上
        （如 i.293.net/2018/style.css 里的 ../images/x.png），不解析就会静默漏抓。
        HTML 里的相对链接本就落在同主机内部、抓取阶段已处理，故默认跳过。
        """
        s = (raw or "").strip()
        if not s or s.lower().startswith(SKIP_SCHEMES):
            return None
        is_abs = s.startswith(("http://", "https://", "//"))
        is_root = s.startswith("/")
        if not is_abs and not is_root and not allow_relative:
            return None

        abs_url = urljoin(page_url, s)
        sp = urlsplit(abs_url)
        if sp.scheme not in ("http", "https") or not self.allowed(abs_url):
            return None

        norm = abs_url.split("#")[0]
        target = self.local_path(norm)
        if not self.exists(target):
            self.candidates += 1
            self.todo.setdefault(target, norm)
        rel = posixpath.relpath(target, cur_dir or ".")
        frag = sp.fragment
        new = rel + ("#" + frag if frag else "")
        # 相对路径解析后若仍指向同一位置，则无需改写（只入队下载）
        return None if new == s else new

    # ---------- 扫描 HTML ----------
    def scan_html(self) -> None:
        for r, _d, fs in os.walk(self.root):
            for f in fs:
                if not f.lower().endswith(HTML_EXTS):
                    continue
                full = os.path.join(r, f)
                rel = os.path.relpath(full, self.root).replace("\\", "/")
                page_url = self.url_of.get(rel)
                if page_url:
                    self.process_html_file(full, rel, page_url)

    def process_html_file(self, full: str, rel: str, page_url: str) -> None:
        try:
            with open(full, encoding="utf-8", errors="surrogateescape") as fh:
                html = fh.read()
        except OSError:
            return
        cur_dir = posixpath.dirname(rel)
        changed = False

        def fix_tag(m: re.Match) -> str:
            nonlocal changed
            tag, attrs = m.group("tag").lower(), m.group("attrs")
            pairs = {mm.group("name").lower(): mm.group("val") for mm in ATTR_RE.finditer(attrs)}
            if tag == "link":
                rel_type = (pairs.get("rel") or "").lower()
                if any(k in rel_type for k in PAGE_LINK_RELS + SKIP_LINK_RELS):
                    return m.group(0)
            names = ASSET_ATTRS.get(tag, set())

            def sub_attr(mm: re.Match) -> str:
                nonlocal changed
                name = mm.group("name").lower()
                if name not in names:
                    return mm.group(0)
                val = mm.group("val")
                if name == "srcset":
                    parts = []
                    for piece in val.split(","):
                        piece = piece.strip()
                        if not piece:
                            continue
                        bits = piece.split()
                        new = self.rewrite_link(bits[0], page_url, cur_dir)
                        if new and new != bits[0]:
                            bits[0] = new
                        parts.append(" ".join(bits))
                    out = ", ".join(parts)
                    if out != val:
                        changed = True
                        return f'{mm.group("name")}={mm.group("q")}{out}{mm.group("q")}'
                    return mm.group(0)
                new = self.rewrite_link(val, page_url, cur_dir)
                if new and new != val:
                    changed = True
                    return f'{mm.group("name")}={mm.group("q")}{new}{mm.group("q")}'
                return mm.group(0)

            new_attrs = ATTR_RE.sub(sub_attr, attrs)
            if new_attrs != attrs:
                return f"<{m.group('tag')}{new_attrs}>"
            return m.group(0)

        new_html = TAG_RE.sub(fix_tag, html)
        if changed:
            if not self.dry_run:
                with open(full, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
                    fh.write(new_html)
            self.edited_html += 1

    # ---------- 扫描已存在的 CSS ----------
    def _guess_url(self, rel: str) -> str:
        """从本地相对路径反推原始 URL（清单里没有该资源时使用）。"""
        parts = rel.split("/")
        if len(parts) < 2 or "." not in parts[0]:
            return ""
        host = parts[0]
        m = re.match(r"^(.+\..+)_(\d+)$", host)
        if m:
            host = f"{m.group(1)}:{m.group(2)}"
        scheme = "https" if self.start_url.startswith("https://") else "http"
        return f"{scheme}://{host}/" + "/".join(parts[1:])

    def scan_css(self) -> None:
        """回扫已存在的 CSS，补齐其中的相对 url()/@import。

        旧版只解析「绝对/根相对」链接，导致 CSS 里的相对图片（如
        url(../images/heart.png)）被静默漏抓。这里按 CSS 自身 URL 解析后入队。
        """
        for r, _d, fs in os.walk(self.root):
            for f in fs:
                if not f.lower().endswith(".css"):
                    continue
                full = os.path.join(r, f)
                rel = os.path.relpath(full, self.root).replace("\\", "/")
                url = self.url_of.get(rel) or self._guess_url(rel)
                if not url:
                    continue
                try:
                    with open(full, encoding="utf-8", errors="surrogateescape") as fh:
                        txt = fh.read()
                except OSError:
                    continue
                new, changed = self.process_css_text(txt, url, rel)
                if changed:
                    self.css_edited += 1
                    if not self.dry_run:
                        with open(full, "w", encoding="utf-8",
                                  errors="surrogateescape", newline="") as fh:
                            fh.write(new)

    # ---------- 下载 ----------
    async def download_round(self) -> int:
        items = list(self.todo.items())
        self.todo.clear()
        if not items:
            return 0
        headers = {"User-Agent": DEFAULT_UA, "Accept": "*/*"}
        limits = httpx.Limits(max_connections=self.concurrency * 2)
        sem = asyncio.Semaphore(self.concurrency)
        ok = 0

        async with httpx.AsyncClient(limits=limits, headers=headers, timeout=20,
                                     follow_redirects=True, verify=False) as client:
            async def one(rel: str, url: str) -> int:
                async with sem:
                    try:
                        r = await client.get(url)
                    except Exception as exc:          # noqa: BLE001
                        self.failed.append({"url": url, "error": str(exc)})
                        return 0
                    if r.status_code >= 400:
                        self.failed.append({"url": url, "status": r.status_code})
                        return 0
                    full = self.abs_path(rel)
                    os.makedirs(os.path.dirname(full), exist_ok=True)
                    with open(full, "wb") as fh:
                        fh.write(r.content)
                    ctype = (r.headers.get("content-type") or "").lower()
                    if is_css_path(rel) or "text/css" in ctype:
                        txt = r.content.decode("utf-8", "replace")
                        new, ch = self.process_css_text(txt, url, rel)
                        if ch:
                            with open(full, "w", encoding="utf-8", newline="") as fh:
                                fh.write(new)
                    return 1

            results = await asyncio.gather(*(one(rel, url) for rel, url in items))
            ok = sum(results)
        self.downloaded += ok
        return ok

    def process_css_text(self, css: str, css_url: str, rel: str) -> tuple[str, bool]:
        cur_dir = posixpath.dirname(rel)

        def repl(m: re.Match) -> str:
            q, u = m.group(1), m.group(2)
            new = self.rewrite_link(u, css_url, cur_dir, allow_relative=True)
            return f"url({q}{new}{q})" if new and new != u else m.group(0)

        out = CSS_URL_RE.sub(repl, css)

        def repl_imp(m: re.Match) -> str:
            q, u = m.group(1), m.group(2)
            new = self.rewrite_link(u, css_url, cur_dir, allow_relative=True)
            return f"@import {q}{new}{q}" if new and new != u else m.group(0)

        out = CSS_IMPORT_RE.sub(repl_imp, out)
        return out, out != css

    # ---------- 主流程 ----------
    async def run(self) -> None:
        print(f"任务目录 : {self.root}")
        print(f"起始主机 : {self.host}    资源范围 : {self.scope}")
        print("扫描 HTML …")
        self.scan_html()
        print("扫描 CSS …")
        self.scan_css()
        uniq = len(self.todo)
        print(f"扫描完成：引用外部资源 {self.candidates} 处，缺失唯一资源 {uniq} 个，"
              f"待改写 HTML {self.edited_html} 个 / CSS {self.css_edited} 个")
        if self.dry_run:
            for rel, url in sorted(self.todo.items()):
                print(f"   [缺] {url}\n        -> {rel}")
            print(f"\n(预演) 将补抓 {uniq} 个资源")
            return

        for rnd in range(1, 5):
            n = await self.download_round()
            print(f"  第 {rnd} 轮：下载 {n} 个；新发现 {len(self.todo)} 个待抓")
            if not self.todo:
                break

        print(f"\n完成：新下载 {self.downloaded} 个资源，改写 {self.edited_html} 个 HTML，"
              f"失败 {len(self.failed)} 个")
        for f in self.failed[:20]:
            print("   失败:", f)


def main() -> int:
    ap = argparse.ArgumentParser(description="就地补抓镜像中缺失的静态资源")
    ap.add_argument("task_dir", help="镜像任务目录（如 downloads/20261011-061903-338184）")
    ap.add_argument("--scope", default="same_site",
                    choices=["same_site", "same_host", "any"], help="资源主机范围")
    ap.add_argument("--dry-run", action="store_true", help="只列出将补抓的资源，不下载")
    args = ap.parse_args()
    if not os.path.isdir(args.task_dir):
        print("目录不存在:", args.task_dir)
        return 1
    asyncio.run(Repairer(args.task_dir, args.scope, args.dry_run).run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
