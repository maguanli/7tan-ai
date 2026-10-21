"""端到端：以 quhao.293.net 为例，验证跨主机静态资源被正确抓取并落盘。

只抓首页（depth=0），对比 asset_scope=same_host 与默认 same_site 的结果。
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crawler import CrawlConfig, Mirror   # noqa: E402

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_e2e_out")


async def run_case(scope: str):
    out = os.path.join(TMP, scope)
    cfg = CrawlConfig(
        start_url="http://quhao.293.net/",
        out_root=out,
        max_depth=0,          # 只看首页
        max_pages=5,
        concurrency=6,
        same_domain=True,
        asset_scope=scope,
        include_assets=True,
        rewrite_links=True,
        timeout=20.0,
        retries=1,
    )
    m = Mirror(cfg)
    st = await m.run()
    files = []
    for r, d, fs in os.walk(out):
        for f in fs:
            files.append(os.path.relpath(os.path.join(r, f), out).replace("\\", "/"))
    return st, sorted(files)


async def main():
    for scope in ("same_host", "same_site"):
        st, files = await run_case(scope)
        print(f"\n=== asset_scope={scope} ===")
        print(f"   页面 {st['pages_ok']} / 资源 {st['assets_ok']} / 文件 {st['files']}")
        for f in files:
            print("   ", f)

    # 检查首页里样式链接是否被本地化
    idx = os.path.join(TMP, "same_site", "quhao.293.net", "index.html")
    if os.path.isfile(idx):
        html = open(idx, encoding="utf-8", errors="replace").read()
        import re
        for m in re.finditer(r'(?:href|src)=(["\'])([^"\']+)\1', html):
            if "style" in m.group(2) or "i.293.net" in m.group(2):
                print("   链接 ->", m.group(2))


if __name__ == "__main__":
    asyncio.run(main())
