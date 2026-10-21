"""
网页镜像爬虫引擎（异步并发）。

职责：
  1. 从起始 URL 广度优先（BFS）递归抓取同站页面与资源；
  2. 每个 URL 按 paths.url_to_relpath 映射成本地路径，**原样保持目录结构**落盘；
  3. 可选重写 HTML/CSS 内的链接为本地相对路径，使离线可直接点击浏览；
  4. 生成 _mirror_manifest.json（URL↔本地路径对照表）与 _mirror_report.txt。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import posixpath
import re
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from .paths import (
    CSS_EXT,
    HTML_EXT,
    guess_ext_by_content_type,
    split_ext,
    url_to_relpath,
)

from .encoding_utils import (
    decode_body,
    ensure_css_utf8_charset,
    to_utf8_text,
)

from .minimal_html import rewrite_html

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 WebMirror/1.0"
)

# 需要改写的标签/属性
LINK_ATTRS = [
    ("a", "href"), ("link", "href"), ("script", "src"), ("img", "src"),
    ("img", "data-src"), ("img", "data-original"), ("source", "src"),
    ("video", "src"), ("video", "poster"), ("audio", "src"),
    ("iframe", "src"), ("frame", "src"), ("embed", "src"),
    ("object", "data"), ("track", "src"), ("input", "src"),
    ("area", "href"), ("form", "action"), ("use", "href"),
]
# 这些标签指向的链接继续作为“页面”入队（参与深度递增）
PAGE_TAGS = {"a", "area", "frame", "iframe"}
# 这些标签指向静态资源
ASSET_TAGS = {"link", "script", "img", "source", "video", "audio", "embed",
              "object", "track", "input"}

CSS_URL_RE = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""", re.I)
CSS_IMPORT_RE = re.compile(r"""@import\s+(['"])([^'"]+)\1""", re.I)

SKIP_SCHEMES = ("javascript:", "mailto:", "tel:", "data:", "blob:",
                "about:", "sms:", "ftp:", "#")


@dataclass
class CrawlConfig:
    """一次镜像任务的抓取配置。"""
    start_url: str = ""
    out_root: str = ""
    max_depth: int = 3            # 页面递归深度（起始页为 0）
    max_pages: int = 300          # 最多抓取页面数
    max_assets: int = 5000        # 最多抓取资源数
    concurrency: int = 8          # 并发数
    same_domain: bool = True      # 仅抓取同站（页面爬取范围）
    asset_scope: str = "same_site"  # 静态资源抓取范围: same_host/same_site/any
    include_assets: bool = True   # 是否下载图片/CSS/JS 等资源
    rewrite_links: bool = True    # 是否把链接改写为本地相对路径
    param_mode: str = "dir"       # query 处理：dir / hash / ignore
    extensionless: str = "index"  # 无扩展名路径：index / html
    with_host_dir: bool = True    # 顶层加域名目录
    host_dir_map: dict[str, str] = field(default_factory=dict)  # 指定 host 改落到别的顶层目录，如 {"a.com": "a.com2"}
    case_safe_file: str = ""      # 大小写安全表 JSON（含 case_safe_paths / requeue_urls）；命中的落盘路径附加 URL 短哈希，规避 Windows 大小写折叠
    obey_robots: bool = False     # 是否遵守 robots.txt
    resume: bool = True           # 断点续抓：输出目录存在 _mirror_state.json 时自动续抓
    delay: float = 0.0            # 每次请求间隔（秒）
    timeout: float = 20.0
    retries: int = 2
    user_agent: str = DEFAULT_UA
    exclude_patterns: list[str] = field(default_factory=list)  # 正则，命中的 URL 跳过
    include_patterns: list[str] = field(default_factory=list)  # 非空时仅抓取命中的 URL
    custom_headers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

# 常见「二级后缀」，用于正确判定主域（如 a.293.com.cn 的主域是 293.com.cn）
_MULTI_SUFFIX = {
    "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn", "ac.cn",
    "com.hk", "com.tw", "com.mo", "com.sg", "com.my", "com.au",
    "com.br", "co.uk", "org.uk", "net.uk", "ac.uk", "gov.uk",
    "co.jp", "co.kr", "co.nz", "co.za", "co.in", "com.tr",
}


def base_domain(host: str) -> str:
    """取主域（注册域）。quhao.293.net -> 293.net；a.b.com.cn -> b.com.cn。

    IP 或单段主机名原样返回。仅做常见二级后缀的启发式判断。
    """
    host = (host or "").lower().strip(".")
    if not host:
        return host
    if host.replace(".", "").isdigit() or ":" in host:   # IPv4 / IPv6
        return host
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    last2 = ".".join(parts[-2:])
    if last2 in _MULTI_SUFFIX and len(parts) >= 3:
        return ".".join(parts[-3:])
    return last2


def normalize_url(url: str, *, keep_query: bool = True) -> str:
    """规范化 URL：去 fragment、统一空路径、小写化 host。"""
    sp = urlsplit(url)
    path = sp.path or "/"
    query = sp.query if keep_query else ""
    host = (sp.hostname or "").lower()
    netloc = host
    if sp.port and sp.port not in (80, 443):
        netloc = f"{host}:{sp.port}"
    return urlunsplit((sp.scheme or "http", netloc, path, query, ""))


def safe_join(root: str, relpath: str) -> str:
    """把相对路径安全地拼到 root 下（防目录穿越）。"""
    relpath = relpath.replace("\\", "/").lstrip("/")
    parts = [p for p in relpath.split("/") if p not in ("", ".", "..")]
    full = os.path.join(root, *parts)
    root_abs = os.path.abspath(root)
    if not os.path.abspath(full).startswith(root_abs):
        raise ValueError(f"非法路径: {relpath}")
    return full


def _atomic_write(path: str, data: bytes) -> None:
    """直接写最终文件（不再走「.part + os.replace」）。

    实测（2026-10-15，youbian 任务；目标目录 youbian.293.net 已积累约 150 万文件）：
      · 直接 open(最终名) + write + close : 2.6 ms
      · open(.part) + write + os.replace  : 4400 ~ 11700 ms
    同一目录、同一 7KB 数据，唯一差别是多了一次重命名，实测慢约 3000 倍。
    32 并发下该重命名还会把 27 个写线程拖进内核态争夺（进程持续烧约 1 个核），
    端到端每项约 12 秒，吞吐被压在 2.7 页/秒，且与 concurrency/delay 无关。

    代价：进程若恰好死在写盘途中，可能留下半个文件。镜像场景可接受
    （清单只在写成功后记账，重跑会覆盖）。要退回旧行为，见同目录
    crawler.py.bak_20261015_directwrite。
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def _append_manifest(path: str, entry: dict) -> None:
    """把一条清单记录追加到 NDJSON 文件（增量落盘，供断点续抓后汇总报告）。

    用单次 os.write + O_APPEND：一次写入即落盘，被强杀时不会留下半截行。
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    # 换行【前置】：万一被强杀撕出半截行，也只污染当前这条，
    # 下一条自带前导换行，不会被粘到残缺记录上（尾部换行格式会连带丢两条）。
    data = ("\n" + json.dumps(entry, ensure_ascii=False)).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def _append_manifest_many(path: str, entries: list) -> None:
    """批量追加清单记录（单次 os.write，显著减少 syscall 与线程池往返）。

    格式仍是「换行前置」：被强杀时撕裂只污染当前那条，不会连带丢下一条。
    批量写由唯一的刷盘协程调用，因此不存在并发写者，无需加锁。
    """
    if not entries:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = "".join("\n" + json.dumps(e, ensure_ascii=False)
                   for e in entries).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


# decode_body() 已移至 encoding_utils（支持 BOM/统计探测/不可靠声明的降级）


# ---------------------------------------------------------------------------
# 镜像爬虫
# ---------------------------------------------------------------------------

class Mirror:
    """单个镜像任务的执行体。"""

    def __init__(self, cfg: CrawlConfig, on_event=None):
        self.cfg = cfg
        self.on_event = on_event
        self.manifest: list[dict] = []
        self.logs: deque = deque(maxlen=800)
        self.stats = {
            "pages_ok": 0, "pages_fail": 0, "assets_ok": 0, "assets_fail": 0,
            "bytes": 0, "files": 0, "skipped": 0,
            "queue_size": 0, "pages_total": 0, "assets_total": 0,
            "started_at": None, "finished_at": None,
        }
        self.errors: list[dict] = []
        self._visited: set[str] = set()
        self._saved: dict[str, str] = {}     # 规范化 URL -> 本地相对路径
        self._lock = asyncio.Lock()
        self._stop = asyncio.Event()
        self._client: httpx.AsyncClient | None = None
        self.queue: asyncio.Queue | None = None
        self._host = urlsplit(cfg.start_url).hostname or ""
        self._allowed_patterns = [re.compile(p) for p in cfg.include_patterns if p]
        self._blocked_patterns = [re.compile(p) for p in cfg.exclude_patterns if p]

        # ---- 断点续抓 ----
        # asyncio.Queue 无法枚举，故用 _pending 镜像一份待抓队列，便于持久化
        self._pending: dict[str, dict] = {}
        self._inflight: dict[str, dict] = {}
        # Windows 上 O_APPEND 并非原子（CRT 是「定位到末尾+写」），
        # 多线程并发追加会互相覆盖，故清单追加必须串行。
        self._manifest_lock = asyncio.Lock()
        self._resumed = False
        self._last_state_save = 0.0
        self._state_lock = asyncio.Lock()
        self._state_path = (os.path.join(cfg.out_root, "_mirror_state.json")
                            if cfg.out_root else "")
        self._ndjson_path = (os.path.join(cfg.out_root, "_mirror_manifest.ndjson")
                             if cfg.out_root else "")
        # 待抓队列流水账：每个 URL 只追加一行，续抓时用「已入队 − 已落盘」精确还原队列
        self._journal_path = (os.path.join(cfg.out_root, "_mirror_queue.tsv")
                              if cfg.out_root else "")
        self._journal = None
        self._journal_n = 0
        # 大小写安全表：命中的落盘路径在扩展名前附加 URL 短哈希，避免 Windows
        # 大小写不敏感导致「两个不同页面写进同一个文件」。_requeue_urls 是需要
        # 强制重抓的 URL（此前已因折叠被覆盖）。
        self._case_safe: set[str] = set()
        self._requeue_urls: set[str] = set()
        # 清单追加改为「单写者 + 批量刷盘」：热路径不再每个文件都加锁 + 跳一次线程池
        self._manifest_buf: list[dict] = []
        self._state_interval = 3.0        # 状态快照节流（秒）

        # 实时速度：只记录「最近完成」的时刻，用于计算最近 60 秒的真实吞吐。
        # 长任务跑久了，累计平均（done/elapsed）会被历史低谷期严重稀释，
        # 明明已经提速，面板上却还是 3.x/秒——所以要单独维护滑动窗口。
        self._recent: deque = deque()
        self._recent_window = 60.0

    # ---------------- 事件与日志 ----------------

    def log(self, msg: str, level: str = "info") -> None:
        entry = {
            "t": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "msg": msg,
        }
        self.logs.append(entry)
        if self.on_event:
            self.on_event("log", entry)

    def _emit_progress(self) -> None:
        if self.on_event:
            self.on_event("progress", self.snapshot())

    def snapshot(self) -> dict:
        st = dict(self.stats)
        if self.queue is not None:
            st["queue_size"] = self.queue.qsize()
        st["visited"] = len(self._visited)
        elapsed = 0.0
        if st.get("started_at"):
            end = st.get("finished_at") or time.time()
            elapsed = end - st["started_at"]
        st["elapsed"] = round(elapsed, 1)
        done = st["pages_ok"] + st["assets_ok"]
        st["speed"] = round(done / elapsed, 1) if elapsed > 1 else done   # 累计平均

        # ---- 最近 N 秒实时速度 ----
        # 先淘汰窗口外的打点，再除以「窗口跨度」；任务刚开始不足一个窗口时，
        # 除以实际已跑时长（否则开跑头几秒会被 60 秒分母严重低估）。
        now = time.time()
        win = self._recent_window
        cutoff = now - win
        while self._recent and self._recent[0] < cutoff:
            self._recent.popleft()
        span = win
        if st.get("started_at"):
            span = min(win, max(0.0, (st.get("finished_at") or now) - st["started_at"]))
        if span >= 1:
            st["speed_recent"] = round(len(self._recent) / span, 1)
        else:
            st["speed_recent"] = float(len(self._recent))
        st["speed_window"] = int(win)
        st["current_urls"] = getattr(self, "_current", [])
        return st

    # ---------------- 主流程 ----------------

    async def run(self) -> dict:
        cfg = self.cfg
        self.stats["started_at"] = time.time()
        os.makedirs(cfg.out_root, exist_ok=True)
        self.log(f"开始镜像：{cfg.start_url}")
        self.log(f"输出目录：{cfg.out_root}")

        if cfg.obey_robots:
            await self._load_robots()

        limits = httpx.Limits(
            max_connections=max(4, cfg.concurrency * 2),
            max_keepalive_connections=max(2, cfg.concurrency),
        )
        headers = {"User-Agent": cfg.user_agent, "Accept": "*/*"}
        headers.update(cfg.custom_headers or {})

        self.queue = asyncio.Queue()
        self._current: list[str] = []
        self._load_case_safe()
        state = self._load_state()
        if state is not None:
            self._restore_state(state)
            self.log(
                f"断点续抓：跳过 {len(self._visited)} 个已处理 URL，"
                f"恢复 {len(self._pending)} 个待抓 URL"
            )
            if self._pending:
                for it in list(self._pending.values()):
                    await self.queue.put(it)
            else:
                self.log("状态文件显示上次已抓完（待抓队列为空）。", "warn")
        else:
            first = {"url": normalize_url(cfg.start_url), "depth": 0, "kind": "page"}
            self._pending[first["url"]] = first
            self._journal_add(first)
            await self.queue.put(first)

        async with httpx.AsyncClient(
            limits=limits, headers=headers, follow_redirects=True,
            timeout=httpx.Timeout(cfg.timeout), verify=False,
        ) as client:
            self._client = client
            workers = [
                asyncio.create_task(self._worker(i))
                for i in range(max(1, cfg.concurrency))
            ]
            flusher = asyncio.create_task(self._manifest_loop())
            try:
                await self.queue.join()
            finally:
                # 退出前落一次状态：把仍在途的任务也记下来，下次好接着抓
                await self._save_state(force=True)
                self._journal_flush()
                for w in workers:
                    w.cancel()
                await asyncio.gather(*workers, return_exceptions=True)
                flusher.cancel()
                await asyncio.gather(flusher, return_exceptions=True)
                await self._flush_manifest()   # 收尾：把缓冲区里剩余的清单条目写完
                self._journal_flush()

        self.stats["finished_at"] = time.time()
        self._write_reports()
        st = self.snapshot()
        self.log(
            f"完成：页面 {st['pages_ok']} 成功 / {st['pages_fail']} 失败，"
            f"资源 {st['assets_ok']} 个，共 {st['files']} 个文件，"
            f"{st['bytes'] / 1024 / 1024:.2f} MB，耗时 {st['elapsed']}s"
        )
        if self.on_event:
            self.on_event("done", st)
        return st

    def stop(self) -> None:
        self._stop.set()
        self.log("收到停止指令，正在优雅退出…", "warn")

    async def _worker(self, idx: int) -> None:
        while True:
            item = await self.queue.get()   # type: ignore[union-attr]
            _k = item.get("url", "")
            self._pending.pop(_k, None)
            self._inflight[_k] = item
            try:
                if self._stop.is_set():
                    # 主动停止：把该项放回待抓队列，便于下次续抓
                    self._pending[_k] = item
                    continue
                await self._handle(item)
            except asyncio.CancelledError:
                raise
            except Exception as exc:        # noqa: BLE001
                url = item.get("url", "")
                self.stats["skipped"] += 1
                self.errors.append({"url": url, "error": str(exc)})
                self.log(f"[失败] {url} -> {exc}", "error")
            finally:
                self._inflight.pop(_k, None)
                self.queue.task_done()
                self._emit_progress()
                await self._save_state()

    # ---------------- 单任务处理 ----------------

    async def _handle(self, item: dict) -> None:
        url, depth, kind = item["url"], item.get("depth", 0), item.get("kind", "page")
        keep_query = self.cfg.param_mode != "ignore"
        key = normalize_url(url, keep_query=keep_query)

        async with self._lock:
            if key in self._visited:
                return
            self._visited.add(key)
            if kind == "page":
                if self.stats["pages_total"] >= self.cfg.max_pages:
                    self.log(f"已达页面上限 {self.cfg.max_pages}，跳过 {url}", "warn")
                    return
                self.stats["pages_total"] += 1
            else:
                if self.stats["assets_total"] >= self.cfg.max_assets:
                    return
                self.stats["assets_total"] += 1

        if self.cfg.delay:
            await asyncio.sleep(self.cfg.delay)

        self._current = [u for u in getattr(self, "_current", [])[-3:] if True] + [url]
        try:
            resp = await self._fetch(url)
        except Exception as exc:            # noqa: BLE001
            if kind == "page":
                self.stats["pages_fail"] += 1
            else:
                self.stats["assets_fail"] += 1
            self.errors.append({"url": url, "error": str(exc)})
            self.log(f"[失败] {url} -> {exc}", "error")
            return

        final_url = normalize_url(str(resp.url), keep_query=keep_query)
        ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()

        relpath = url_to_relpath(
            final_url,
            param_mode=self.cfg.param_mode,
            extensionless=self.cfg.extensionless,
            with_host=self.cfg.with_host_dir,
            host_dir_map=self.cfg.host_dir_map,
            case_safe_paths=self._case_safe,
        )

        # 无扩展名 + 非 HTML 资源（如 /avatar/123 返回图片）→ 补真实扩展名
        base, ext = split_ext(relpath)
        if not ext:
            guess = guess_ext_by_content_type(ctype)
            if guess:
                relpath = base + guess
                ext = guess

        is_html = ctype in ("text/html", "application/xhtml+xml") or ext in HTML_EXT
        is_css = ctype == "text/css" or ext in CSS_EXT

        if resp.status_code >= 400:
            self.log(f"[{resp.status_code}] {url}", "warn")

        if is_html:
            body = decode_body(resp)
            body = self._process_html(body, final_url, relpath, depth)
            await self._write(relpath, body.encode("utf-8"), url, ctype, resp.status_code)
            self.stats["pages_ok"] += 1
        elif is_css:
            body = decode_body(resp)
            body = self._process_css(body, final_url, relpath, depth)
            await self._write(relpath, body.encode("utf-8"), url, ctype, resp.status_code)
            if kind == "page":
                self.stats["pages_ok"] += 1
            else:
                self.stats["assets_ok"] += 1
        else:
            data = to_utf8_text(resp.content, relpath, ctype)
            await self._write(relpath, data, url, ctype, resp.status_code)
            if kind == "page":
                self.stats["pages_ok"] += 1
            else:
                self.stats["assets_ok"] += 1

        # 记录 URL ↔ 路径 映射（原始 URL 与重定向后 URL 都登记）
        async with self._lock:
            self._saved[key] = relpath
            self._saved[final_url] = relpath

    async def _fetch(self, url: str) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self.cfg.retries + 1):
            try:
                resp = await self._client.get(url)   # type: ignore[union-attr]
                if resp.status_code >= 500 and attempt < self.cfg.retries:
                    raise httpx.HTTPStatusError(
                        f"HTTP {resp.status_code}", request=resp.request, response=resp
                    )
                return resp
            except Exception as exc:        # noqa: BLE001
                last_exc = exc
                if attempt < self.cfg.retries:
                    await asyncio.sleep(0.6 * (attempt + 1))
        raise last_exc if last_exc else RuntimeError("unknown error")

    async def _write(self, relpath: str, data: bytes, url: str,
                     ctype: str, status: int) -> None:
        full = safe_join(self.cfg.out_root, relpath)
        entry = {
            "url": url,
            "path": relpath,
            "size": len(data),
            "content_type": ctype,
            "status": status,
        }
        await asyncio.to_thread(_atomic_write, full, data)
        # 清单增量落盘（NDJSON）：此处只做内存 append，由后台协程批量刷盘。
        # 好处：热路径不再有「加锁 + 线程池往返」；且刷盘只有一个写者，
        # 天然规避 Windows 上 O_APPEND 非原子导致的并发覆盖。
        if self._ndjson_path:
            self._manifest_buf.append(entry)
        self.stats["files"] += 1
        self.stats["bytes"] += len(data)
        self.manifest.append(entry)
        # 实时速度打点：_write 每落盘一个页面/资源都会走到这里，
        # 与 pages_ok + assets_ok 的口径完全一致。
        self._recent.append(time.time())

    # ---------------- 链接处理 ----------------

    def _is_allowed(self, url: str, kind: str = "page") -> bool:
        sp = urlsplit(url)
        if sp.scheme not in ("http", "https"):
            return False
        host = (sp.hostname or "").lower()
        if self.cfg.same_domain:
            same_host = host == self._host or host.endswith("." + self._host)
            if kind == "page":
                # 页面爬取：始终限制在起始主机（及其子域）内
                if not same_host:
                    return False
            else:
                # 静态资源：按 asset_scope 决定允许的主机范围
                scope = self.cfg.asset_scope
                if scope == "same_host":
                    if not same_host:
                        return False
                elif scope == "same_site":
                    if not same_host and base_domain(host) != base_domain(self._host):
                        return False
                # scope == "any": 不限制资源主机（含第三方 CDN）
        if self._blocked_patterns and any(p.search(url) for p in self._blocked_patterns):
            return False
        if self._allowed_patterns and not any(p.search(url) for p in self._allowed_patterns):
            return False
        return True

    def _map_to_local(self, raw: str, base_url: str, cur_dir: str, kind: str = "page") -> str | None:
        """把页面内的一个链接换算成本地相对路径；返回 None = 保持原样。"""
        if not raw:
            return None
        s = raw.strip()
        if s.startswith(SKIP_SCHEMES) or s.startswith("//#"):
            return None
        abs_url = urljoin(base_url, s)
        sp = urlsplit(abs_url)
        if sp.scheme not in ("http", "https"):
            return None
        if not self._is_allowed(abs_url, kind):
            return None
        norm = urlunsplit((sp.scheme, sp.netloc, sp.path or "/", sp.query, ""))
        target_rel = url_to_relpath(
            norm,
            param_mode=self.cfg.param_mode,
            extensionless=self.cfg.extensionless,
            with_host=self.cfg.with_host_dir,
            host_dir_map=self.cfg.host_dir_map,
            case_safe_paths=self._case_safe,
        )
        rel = posixpath.relpath(target_rel, cur_dir or ".")
        if sp.fragment:
            rel += "#" + sp.fragment
        return rel

    def _enqueue_link(self, raw: str, base_url: str, depth: int, kind: str) -> None:
        if not raw:
            return
        s = raw.strip()
        if s.startswith(SKIP_SCHEMES):
            return
        abs_url = urljoin(base_url, s)
        sp = urlsplit(abs_url)
        if sp.scheme not in ("http", "https"):
            return
        if sp.path.lower().endswith(".pdf") or s.startswith("//#"):  # pdf 也抓，但按资源
            pass
        if not self._is_allowed(abs_url, kind):
            return
        if kind == "page" and depth > self.cfg.max_depth:
            return
        norm = urlunsplit((sp.scheme, sp.netloc, sp.path or "/", sp.query, ""))
        # 去重：已处理过或已在队列中的 URL 不再重复入队
        if norm in self._visited or norm in self._pending:
            return
        item = {"url": norm, "depth": depth, "kind": kind}
        self._pending[norm] = item
        self._journal_add(item)
        self.queue.put_nowait(item)  # type: ignore[union-attr]

    def _process_html(self, html: str, base_url: str, relpath: str, depth: int) -> str:
        """改写 HTML 内的链接为本地相对路径；其余字节保持原样。

        采用最小化改写（见 app.minimal_html），不再用 BeautifulSoup 重新序列化
        整个文档——那会重排属性顺序、给 void 元素补 `/>`、统一引号，从而改变原站代码。
        """
        cur_dir = posixpath.dirname(relpath)

        # 需要在 attr_map 中处理的标签/属性集合
        want: dict[str, set] = {}
        for t, a in LINK_ATTRS:
            want.setdefault(t, set()).add(a)
        want.setdefault("img", set()).add("srcset")
        want.setdefault("source", set()).add("srcset")

        def rewrite_one(tag: str, attr: str, value: str, attrs: dict) -> str | None:
            if attr == "srcset":
                return self._rewrite_srcset(value, base_url, cur_dir, depth)
            sub = "page" if (tag in PAGE_TAGS or tag == "a") else "asset"
            if tag == "link" and attr == "href":
                rel_type = str(attrs.get("rel", "") or "")
                if "canonical" in rel_type or "alternate" in rel_type:
                    sub = "page"
            if self.cfg.include_assets or sub == "page":
                self._enqueue_link(value, base_url, depth + (1 if sub == "page" else 0), sub)
            if self.cfg.rewrite_links:
                return self._map_to_local(value, base_url, cur_dir, sub)
            return None

        def attr_map(tag: str, attr: str, value: str, attrs: dict) -> str | None:
            if attr in want.get(tag, ()):
                return rewrite_one(tag, attr, value, attrs)
            return None

        def style_map(css: str) -> str:
            return self._rewrite_css_text(css, base_url, cur_dir, depth)

        return rewrite_html(html, attr_map=attr_map, style_map=style_map, ensure_charset=True)

    def _rewrite_srcset(self, value: str, base_url: str, cur_dir: str, depth: int) -> str:
        """改写 srcset="url 1x, url2 2x" 里的每个 URL。"""
        out = []
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            bits = part.split()
            u = bits[0]
            if self.cfg.include_assets:
                self._enqueue_link(u, base_url, depth, "asset")
            if self.cfg.rewrite_links:
                new = self._map_to_local(u, base_url, cur_dir, "asset")
                if new:
                    bits[0] = new
            out.append(" ".join(bits))
        return ", ".join(out)

    def _process_css(self, css: str, base_url: str, relpath: str, depth: int) -> str:
        cur_dir = posixpath.dirname(relpath)
        css = self._rewrite_css_text(css, base_url, cur_dir, depth)
        return ensure_css_utf8_charset(css)

    def _rewrite_css_text(self, text: str, base_url: str, cur_dir: str, depth: int,
                          kind: str = "asset") -> str:
        def repl(m: re.Match) -> str:
            quote, u = m.group(1), m.group(2)
            if self.cfg.include_assets:
                self._enqueue_link(u, base_url, depth, kind)
            if self.cfg.rewrite_links:
                new = self._map_to_local(u, base_url, cur_dir, kind)
                if new:
                    return f"url({quote}{new}{quote})"
            return m.group(0)

        text = CSS_URL_RE.sub(repl, text)

        def repl_imp(m: re.Match) -> str:
            quote, u = m.group(1), m.group(2)
            if self.cfg.include_assets:
                self._enqueue_link(u, base_url, depth + 1, kind)
            if self.cfg.rewrite_links:
                new = self._map_to_local(u, base_url, cur_dir, kind)
                if new:
                    return f"@import {quote}{new}{quote}"
            return m.group(0)

        return CSS_IMPORT_RE.sub(repl_imp, text)

    # ---------------- robots / 报告 ----------------

    async def _load_robots(self) -> None:
        sp = urlsplit(self.cfg.start_url)
        robots_url = f"{sp.scheme}://{sp.netloc}/robots.txt"
        try:
            r = await self._client.get(robots_url)   # type: ignore[union-attr]
            if r.status_code == 200:
                disallow = []
                for line in r.text.splitlines():
                    line = line.split("#")[0].strip()
                    if line.lower().startswith("disallow:"):
                        p = line.split(":", 1)[1].strip()
                        if p:
                            disallow.append(re.compile(r"^" + re.escape(p).replace(r"\*", ".*")))
                if disallow:
                    self._blocked_patterns.extend(disallow)
                    self.log(f"已加载 robots.txt，{len(disallow)} 条 Disallow 规则")
        except Exception as exc:            # noqa: BLE001
            self.log(f"robots.txt 读取失败（忽略）: {exc}", "warn")

    # ---------------- 断点续抓 ----------------

    def _journal_add(self, item: dict) -> None:
        """把新入队的 URL 追加进流水账（同一 URL 只会在首次入队时写入）。"""
        if not self._journal_path:
            return
        try:
            if self._journal is None:
                os.makedirs(os.path.dirname(self._journal_path) or ".", exist_ok=True)
                # 行缓冲：每写一行立即落盘，被强杀也最多丢当前这一行
                self._journal = open(self._journal_path, "a", encoding="utf-8",
                                     buffering=1)
            # 换行【前置】，理由同 _append_manifest：撕裂只污染当前那条
            self._journal.write(
                f"\n{item.get('depth', 0)}\t{item.get('kind', 'page')}\t{item['url']}"
            )
            self._journal_n += 1
        except Exception:                   # noqa: BLE001
            pass

    def _journal_flush(self) -> None:
        try:
            if self._journal is not None:
                self._journal.flush()
        except Exception:                   # noqa: BLE001
            pass

    def _load_journal(self) -> list[dict]:
        """读回流水账：曾经入队过的全部 URL。"""
        if not (self._journal_path and os.path.isfile(self._journal_path)):
            return []
        out: dict[str, dict] = {}
        try:
            with open(self._journal_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    parts = line.rstrip("\n").split("\t", 2)
                    if len(parts) != 3:
                        continue
                    d, k, u = parts
                    if not u or u in out:
                        continue
                    if not u.startswith(("http://", "https://")):
                        continue     # 被撕裂的半截记录，直接忽略
                    try:
                        d = int(d)
                    except ValueError:
                        d = 0
                    if k not in ("page", "asset"):
                        k = "page"
                    out[u] = {"url": u, "depth": d, "kind": k}
        except Exception:                   # noqa: BLE001
            return list(out.values())
        return list(out.values())

    def _load_case_safe(self) -> None:
        """加载「大小写安全」表：命中路径附加短哈希；并记录需强制重抓的 URL。"""
        path = self.cfg.case_safe_file
        if not path:
            path = (os.path.join(self.cfg.out_root, "_case_safe.json")
                    if self.cfg.out_root else "")
        if not path or not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:            # noqa: BLE001
            self.log(f"大小写安全表读取失败（忽略）: {exc}", "warn")
            return
        if isinstance(data, dict):
            vals = data.get("case_safe_paths") or []
            rq = data.get("requeue_urls") or []
        else:
            vals, rq = data, []
        if isinstance(vals, list):
            self._case_safe = {str(v).lower() for v in vals}
        if isinstance(rq, list):
            self._requeue_urls = {str(u) for u in rq}
        self.log(f"大小写安全表已加载：冲突路径 {len(self._case_safe)} 个，"
                 f"待重抓 URL {len(self._requeue_urls)} 个")

    def _load_state(self) -> dict | None:
        """读取上次中断留下的状态文件；不适用时返回 None（走全新抓取）。"""
        if not (self.cfg.resume and self._state_path):
            return None
        if not os.path.isfile(self._state_path):
            return None
        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:            # noqa: BLE001
            self.log(f"状态文件读取失败（忽略续抓）: {exc}", "warn")
            return None
        if data.get("start_url") != self.cfg.start_url:
            self.log("状态文件与本次起始网址不一致，忽略续抓。", "warn")
            return None
        return data

    def _load_manifest(self) -> list[dict]:
        """从 NDJSON 增量清单恢复完整清单（跨中断累计）。"""
        if not (self._ndjson_path and os.path.isfile(self._ndjson_path)):
            return []
        out: list[dict] = []
        try:
            with open(self._ndjson_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except Exception:       # noqa: BLE001
                        continue
        except Exception:                   # noqa: BLE001
            pass
        # 同一路径可能因重定向/续抓重写过，按路径去重（保留最后一条）
        dedup: dict[str, dict] = {}
        for e in out:
            p = e.get("path")
            if p:
                dedup[p] = e
        return list(dedup.values())

    def _restore_state(self, state: dict) -> None:
        """恢复已处理集合、待抓队列、计数器与清单。"""
        inflight = [it for it in (state.get("inflight") or [])
                    if isinstance(it, dict) and it.get("url")]
        self._visited = set(state.get("visited") or [])
        # 在途任务尚未完成，从 visited 剔除，让它们重新入队
        for it in inflight:
            self._visited.discard(it["url"])
        self._saved = dict(state.get("saved") or {})
        self.errors = list(state.get("errors") or [])
        st = state.get("stats") or {}
        for k in ("pages_ok", "pages_fail", "assets_ok", "assets_fail",
                  "bytes", "files", "skipped", "pages_total", "assets_total"):
            if isinstance(st.get(k), int):
                self.stats[k] = st[k]
        self.stats["started_at"] = st.get("started_at") or time.time()
        self.stats["finished_at"] = None
        for it in list(state.get("queue") or []) + inflight:
            if isinstance(it, dict) and it.get("url"):
                self._pending[it["url"]] = it
        self.manifest = self._load_manifest()
        # 关键：清单（NDJSON 逐条追加）比状态快照更“新鲜”。
        # 把清单里已落盘的 URL 也并入已处理集合，避免状态快照落后导致重复抓取。
        done: set[str] = set()
        for e in self.manifest:
            u = e.get("url")
            p = e.get("path")
            if u:
                done.add(u)
                self._visited.add(u)
                self._visited.add(normalize_url(u))
            # saved（URL→本地路径）同样从清单重建：续抓后新抓的页面
            # 仍能把指向「上次已下载页面」的链接改写成正确的本地相对路径
            if u and p:
                self._saved.setdefault(u, p)
                self._saved.setdefault(normalize_url(u), p)
        # 用流水账精确还原待抓队列：曾入队 − 已落盘（不受状态快照滞后影响）
        journal = self._load_journal()
        if journal:
            self._pending = {it["url"]: it for it in journal if it["url"] not in done}
        else:
            # 老版本没有流水账，退回状态快照里的队列（可能丢掉最后几秒）
            self._pending = {k: v for k, v in self._pending.items()
                             if k not in done and k not in self._visited}
        for u in list(self._pending):
            self._visited.discard(u)
        # 计数器从清单精确重算（状态快照会滞后，导致计数偏小）
        html_ct = ("text/html", "application/xhtml+xml")
        self.stats["files"] = len(done)
        self.stats["bytes"] = sum(int(e.get("size") or 0) for e in self.manifest)
        pages = sum(1 for e in self.manifest if e.get("content_type") in html_ct)
        self.stats["pages_ok"] = pages
        self.stats["assets_ok"] = max(0, len(done) - pages)
        # ---- 大小写折叠重抓：把此前被覆盖的 URL 强制重新排队 ----
        if self._case_safe and self._requeue_urls:
            recrawled: set[str] = set()
            for e in self.manifest:
                u = e.get("url")
                if u and u in self._requeue_urls:
                    p = e.get("path") or ""
                    if hashlib.md5(u.encode("utf-8")).hexdigest()[:8] in p:
                        recrawled.add(u)
            n_rq = 0
            for u in self._requeue_urls:
                if u in recrawled:
                    continue
                self._visited.discard(u)
                self._visited.discard(normalize_url(u))
                self._pending[u] = {"url": u, "depth": 0, "kind": "page"}
                n_rq += 1
            if n_rq:
                self.log(f"大小写折叠重抓：强制重新入队 {n_rq} 个 URL"
                         f"（已重抓 {len(recrawled)} 个）", "warn")
        self._resumed = True

    async def _manifest_loop(self) -> None:
        """清单刷盘协程（唯一的清单写者）：每 0.5 秒把缓冲区批量追加落盘。"""
        while True:
            await asyncio.sleep(0.5)
            await self._flush_manifest()

    async def _flush_manifest(self) -> None:
        """把缓冲区里的清单条目一次性追加落盘。

        批量单次 os.write：既省 syscall，又让线程池只往返一次而不是每个文件一次。
        写失败时把条目放回缓冲区，下轮重试（数据不丢）。
        """
        if not self._ndjson_path or not self._manifest_buf:
            return
        buf, self._manifest_buf = self._manifest_buf, []
        try:
            await asyncio.to_thread(_append_manifest_many, self._ndjson_path, buf)
        except Exception as exc:            # noqa: BLE001
            self._manifest_buf = buf + self._manifest_buf
            self.log(f"清单写入失败: {exc}", "warn")

    async def _save_state(self, force: bool = False) -> None:
        """把抓取进度落盘（默认 3 秒节流），供中断后续抓。

        性能要点（实测教训，勿回退）
        ----------------------------
        早期版本把 visited / queue / saved 三个**全量集合**一并写进快照，
        体积随抓取量线性增长：实测 youbian 任务跑到 28.5 万 URL 时快照达
        **87.2 MB**，json.dumps 单次耗时 **1.34 秒**，而且是在**事件循环
        线程**上序列化的 —— 每 5 秒把所有 worker 冻结 1.34 秒（占空比
        27%），于是越抓越慢。

        这三个集合其实都能精确重建，不必整体落盘：
          · queue（待抓）    = _mirror_queue.ndjson（入队流水） − 已落盘
          · visited（已处理）= 已落盘清单（+ 失败 URL，见 _restore_state）
          · saved（URL→路径）= 已落盘清单里的 url / path 字段
        因此快照只保留小标量与尾部错误，体积稳定在 KB 级，序列化耗时可忽略。
        """
        if not (self.cfg.resume and self._state_path):
            return
        # 节流判断前移到加锁之前：绝大多数调用在此直接返回，不再争抢锁
        now = time.time()
        if not force and (now - self._last_state_save) < self._state_interval:
            return
        async with self._state_lock:
            now = time.time()
            if not force and (now - self._last_state_save) < self._state_interval:
                return
            self._last_state_save = now
            payload = {
                "version": 2,
                "start_url": self.cfg.start_url,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "queue_empty_snapshot": self.queue is not None and self.queue.empty(),
                "inflight": list(self._inflight.values()),
                "stats": self.stats,
                "errors": self.errors[-1000:],
                # 下面两个计数仅供界面展示/自检，真正的队列由流水账+清单重建
                "pending_count": len(self._pending),
                "visited_count": len(self._visited),
            }
            try:
                await asyncio.to_thread(
                    _atomic_write, self._state_path,
                    json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                )
            except Exception as exc:        # noqa: BLE001
                self.log(f"状态保存失败: {exc}", "warn")
            self._journal_flush()

    def _write_reports(self) -> None:
        try:
            os.makedirs(self.cfg.out_root, exist_ok=True)
            manifest_path = os.path.join(self.cfg.out_root, "_mirror_manifest.json")
            # 按路径去重（续抓/重定向可能产生重复条目），保留最后一条
            dedup: dict[str, dict] = {}
            for e in self.manifest:
                key = e.get("path") or e.get("url") or ""
                dedup[key] = e
            self.manifest = list(dedup.values())
            payload = {
                "start_url": self.cfg.start_url,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "config": self.cfg.to_dict(),
                "stats": self.snapshot(),
                "files": self.manifest,
                "errors": self.errors,
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            lines = [
                "WebMirror 镜像报告",
                "=" * 60,
                f"起始网址 : {self.cfg.start_url}",
                f"输出目录 : {self.cfg.out_root}",
                f"生成时间 : {datetime.now():%Y-%m-%d %H:%M:%S}",
                f"最大深度 : {self.cfg.max_depth}   并发: {self.cfg.concurrency}",
                "-" * 60,
            ]
            st = self.snapshot()
            lines += [
                f"页面成功 : {st['pages_ok']}",
                f"页面失败 : {st['pages_fail']}",
                f"资源成功 : {st['assets_ok']}",
                f"资源失败 : {st['assets_fail']}",
                f"文件总数 : {len(self.manifest) or st['files']}",
                f"总大小   : {st['bytes'] / 1024 / 1024:.2f} MB",
                f"耗时     : {st['elapsed']} 秒",
                "=" * 60,
                "URL → 本地路径 对照表（前 200 条）：",
            ]
            for f in self.manifest[:200]:
                lines.append(f"{f['path']}    <=  {f['url']}")
            if self.errors:
                lines += ["", "失败列表："]
                for e in self.errors[:100]:
                    lines.append(f"{e['url']}  ->  {e['error']}")
            with open(os.path.join(self.cfg.out_root, "_mirror_report.txt"),
                      "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception as exc:            # noqa: BLE001
            self.log(f"报告写入失败: {exc}", "warn")
