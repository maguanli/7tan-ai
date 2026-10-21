"""真实站点端到端验证：镜像 www.cnr.cn（gb2312 站点），检查中文是否正常。"""
import asyncio
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crawler import CrawlConfig, Mirror            # noqa: E402
from app.encoding_utils import COMMON_HANZI            # noqa: E402

URL = "http://www.cnr.cn/"
OUT_TXT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "real_site_result.txt")


async def main():
    tmp = tempfile.mkdtemp(prefix="cnr_mirror_")
    cfg = CrawlConfig(start_url=URL, out_root=tmp, max_depth=1, max_pages=3,
                      max_assets=12, concurrency=4, same_domain=True,
                      rewrite_links=True, include_assets=True, obey_robots=False)
    m = Mirror(cfg)
    await m.run()

    lines = [f"镜像 {URL} -> {tmp}",
             f"页面 {m.stats['pages_ok']} 成功 / {m.stats['pages_fail']} 失败，"
             f"资源 {m.stats['assets_ok']} 成功 / {m.stats['assets_fail']} 失败，"
             f"共 {m.stats['files']} 个文件", ""]

    checked = bad = 0
    for root, _dirs, files in os.walk(tmp):
        for fn in files:
            if not fn.endswith((".html", ".htm", ".css", ".js")):
                continue
            full = os.path.join(root, fn)
            raw = open(full, "rb").read()
            rel = os.path.relpath(full, tmp)
            try:
                text = raw.decode("utf-8")
                decode_ok = True
            except UnicodeDecodeError:
                text, decode_ok = "", False
            hanzi = [c for c in text if "\u4e00" <= c <= "\u9fff"]
            hit = sum(1 for c in hanzi if c in COMMON_HANZI)
            ratio = (hit / len(hanzi)) if hanzi else 0.0
            has_replacement = "\ufffd" in text
            # 文件里声明的字符集
            m2 = re.search(rb"charset=[\"']?([\w\-]+)", raw[:2048], re.I)
            declared = m2.group(1).decode("ascii") if m2 else "(none)"

            ok = decode_ok and not has_replacement and (ratio >= 0.5 or not hanzi)
            checked += 1
            bad += 0 if ok else 1
            lines.append(
                f"{'OK ' if ok else 'BAD'} {rel}\n"
                f"   声明={declared} utf8解码={'成功' if decode_ok else '失败'} "
                f"U+FFFD={has_replacement} 汉字={len(hanzi)} 常用字占比={ratio:.0%}\n"
                f"   片段: {text[:160]!r}")

    lines.append("")
    lines.append(f"结论: 检查 {checked} 个文本文件，异常 {bad} 个 "
                 f"-> {'全部正常' if bad == 0 else '存在乱码'}")
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"checked={checked} bad={bad} -> {OUT_TXT}")


if __name__ == "__main__":
    asyncio.run(main())
