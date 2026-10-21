"""
端到端编码回归测试：起本地站点（GBK/UTF-8/错配/无声明），整站镜像后
按「浏览器的方式」把落盘文件读回来，检查是否还会乱码。

用法： python tests/repro_encoding.py
结果： tests/repro_result.txt
"""
import asyncio
import os
import re
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

try:                      # 控制台可能是 GBK，避免打印 emoji 报错
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:         # noqa: BLE001
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crawler import CrawlConfig, Mirror  # noqa: E402

CN = "\u4e2d\u6587"          # 中文
PAGE = "\u9875\u9762"        # 页面
STYLE = "\u6837\u5f0f"       # 样式
SCRIPT = "\u811a\u672c"      # 脚本

# GBK 页面：meta charset=gbk  + 外链 GBK 的 CSS/JS
GBK_PAGE = f"""<!DOCTYPE html>
<html><head><meta charset="gbk"><title>{CN}\u6d4b\u8bd5\u9875</title>
<link rel="stylesheet" href="/css/style.css"></head>
<body><h1>{CN}\u6807\u9898\uff1a\u7f51\u9875\u955c\u50cf</h1>
<p>{CN}\u6b63\u6587\uff0c\u7528\u4e8e\u68c0\u9a8c\u7f16\u7801\u3002</p>
<script src="/js/app.js"></script></body></html>
"""
GBK_CSS = f'@charset "gbk";\n.box::after{{content:"{CN}{STYLE}";color:red}}\n'
GBK_JS = f'var msg = "{CN}{SCRIPT}\u63d0\u793a";\n'

# 完全无声明 + GBK 内容（最容易中途被猜错）
GBK_NO_META = (f"<!DOCTYPE html><html><head><title>T</title></head>"
               f"<body><p>{CN}\u65e0\u58f0\u660e\u4f46\u662fGBK</p></body></html>")

UTF8_WRONG_HDR = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>T</title></head>
<body><p>{CN}\u6b63\u6587\uff0c\u670d\u52a1\u5668\u5934\u5374\u8bf4\u81ea\u5df1\u662f latin-1\u3002</p>
</body></html>"""

NO_CHARSET_UTF8 = (f"<!DOCTYPE html><html><head><title>T</title></head>"
                   f"<body><p>{CN}\u65e0\u4efb\u4f55\u58f0\u660e</p></body></html>")

HTTP_EQUIV_GBK = f"""<!DOCTYPE html>
<html><head><meta http-equiv="Content-Type" content="text/html; charset=gbk">
<title>T</title></head><body><p>{CN}http-equiv \u5f62\u5f0f</p></body></html>"""

PORT = 8795
RESULTS = []


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/gbk/page"):
            self._send(GBK_PAGE.encode("gbk"), "text/html; charset=gbk")
        elif self.path.startswith("/css/"):
            self._send(GBK_CSS.encode("gbk"), "text/css; charset=gbk")
        elif self.path.startswith("/js/"):
            self._send(GBK_JS.encode("gbk"), "application/javascript; charset=gbk")
        elif self.path.startswith("/gbknometa"):
            self._send(GBK_NO_META.encode("gbk"), "text/html")
        elif self.path.startswith("/wronghdr"):
            self._send(UTF8_WRONG_HDR.encode("utf-8"), "text/html; charset=iso-8859-1")
        elif self.path.startswith("/nometa"):
            self._send(NO_CHARSET_UTF8.encode("utf-8"), "text/html")
        elif self.path.startswith("/httpequiv"):
            self._send(HTTP_EQUIV_GBK.encode("gbk"), "text/html; charset=gbk")
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()


def browser_decode(path):
    """模拟浏览器读取本地文件，取它实际会用的字符集。

    HTML  : 看 <meta charset=...>；没有就按中文 Windows 的默认(GBK)猜
    CSS   : 看 @charset "..."；没有则按规范默认 UTF-8
    JS/其他: 跟随引用它的文档（HTML 已声明 utf-8），即 UTF-8
    """
    raw = open(path, "rb").read()
    ext = os.path.splitext(path)[1].lower()
    m = re.search(rb"charset=[\"']?([\w\-]+)", raw[:2048], re.I)
    if not m:
        m = re.search(rb"@charset\s+[\"']([\w\-]+)", raw[:200], re.I)
    declared = m.group(1).decode("ascii") if m else None
    if not declared:
        if ext in (".html", ".htm"):
            return "(无声明→按GBK猜)", raw.decode("gbk", errors="replace"), raw
        return "(跟随文档→utf-8)", raw.decode("utf-8", errors="replace"), raw
    if ext in (".html", ".htm") and declared.lower() in ("gbk", "gb2312"):
        # HTML 若还声明 GBK，浏览器就会按 GBK 解 → 这正是我们要排除的乱码场景
        return declared, raw.decode(declared, errors="replace"), raw
    try:
        return declared, raw.decode(declared, errors="replace"), raw
    except LookupError:
        return declared, raw.decode("utf-8", errors="replace"), raw


async def mirror(url, out):
    cfg = CrawlConfig(start_url=url, out_root=out, max_depth=1, max_pages=8,
                      max_assets=8, concurrency=2, same_domain=True,
                      rewrite_links=True, include_assets=True, obey_robots=False)
    m = Mirror(cfg)
    await m.run()
    return m


def check(root, label, subpath, expect_marker, extra_check=None):
    full = os.path.join(root, subpath)
    if not os.path.exists(full):
        RESULTS.append(f"[{label}] ❌ 文件不存在: {subpath}")
        return False
    declared, text, raw = browser_decode(full)
    ok = expect_marker in text
    if extra_check:
        ok = ok and extra_check(raw, text)
    RESULTS.append(
        f"[{label}] {'✅ 正常' if ok else '❌ 乱码/异常'}  {subpath}\n"
        f"      声明={declared}  大小={len(raw)}B\n"
        f"      浏览器看到: {text[-110:]!r}")
    return ok


def main():
    srv = HTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{PORT}"
    tmp = tempfile.mkdtemp(prefix="enc_repro_")
    allok = True

    # 站点 1：GBK 页面 + 外链 GBK 的 CSS/JS
    d1 = os.path.join(tmp, "site1")
    asyncio.run(mirror(f"{base}/gbk/page.html", d1))
    h = f"127.0.0.1_{PORT}"
    allok &= check(d1, "1a GBK页面", f"{h}/gbk/page.html", f"{CN}\u6807\u9898")
    allok &= check(d1, "1b GBK-CSS", f"{h}/css/style.css", f"{CN}{STYLE}",
                   extra_check=lambda raw, t: b'@charset "utf-8"' in raw)
    allok &= check(d1, "1c GBK-JS", f"{h}/js/app.js", f"{CN}{SCRIPT}",
                   extra_check=lambda raw, t: raw.decode("utf-8") is not None)

    # 站点 2~5
    cases = [
        ("2 头谎报latin1", "/wronghdr/page.html", f"{CN}\u6b63\u6587"),
        ("3 无charset声明", "/nometa/page.html", f"{CN}\u65e0\u4efb\u4f55"),
        ("4 http-equiv式", "/httpequiv/page.html", f"{CN}http-equiv"),
        ("5 无声明+GBK", "/gbknometa/page.html", f"{CN}\u65e0\u58f0\u660e"),
    ]
    for label, urlpath, expect in cases:
        d = os.path.join(tmp, label.split()[0])
        asyncio.run(mirror(base + urlpath, d))
        rel = urlpath.strip("/").split("/")[0]
        allok &= check(d, label, f"127.0.0.1_{PORT}/{rel}/page.html", expect)

    srv.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

    head = "ALL PASS" if allok else "SOME FAILED"
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "repro_result.txt"), "w", encoding="utf-8") as f:
        f.write(head + "\n\n" + "\n\n".join(RESULTS) + "\n")
    print(head, "-> see tests/repro_result.txt")


if __name__ == "__main__":
    main()
