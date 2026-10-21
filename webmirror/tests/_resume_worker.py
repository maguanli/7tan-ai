"""子进程抓取器：供 test_resume.py 模拟"跑到一半被强杀"。"""
import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.crawler import CrawlConfig, Mirror   # noqa: E402


async def main() -> None:
    cfg = CrawlConfig(
        start_url=sys.argv[1],
        out_root=sys.argv[2],
        max_depth=10,
        max_pages=100000,
        max_assets=5000,
        concurrency=4,
        delay=0.05,
        same_domain=True,
        include_assets=True,
        rewrite_links=True,
        resume=True,
        timeout=20.0,
        retries=1,
    )
    await Mirror(cfg).run()


if __name__ == "__main__":
    asyncio.run(main())
