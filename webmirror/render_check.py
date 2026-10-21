# -*- coding: utf-8 -*-
"""用真浏览器渲染镜像页面并实测（需先启动服务：python run.py）。

报告：加载的样式表数 / CSS 规则总数、关键元素计算样式、图片是否真的加载、
jQuery 等库是否可用、失败请求列表；同时输出整页截图，便于肉眼复核。

用法：
    python render_check.py <任务ID> <页面相对路径> [--shot docs/xxx.png]
    python render_check.py 20261011-063405-6a6904 anquanqi.293.net/index.html
"""
import argparse
import glob
import json
import os
import sys

from playwright.sync_api import sync_playwright

CHROME_CANDIDATES = [
    os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright\chromium-*\chrome-win64\chrome.exe"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_chrome() -> str | None:
    for pat in CHROME_CANDIDATES:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_id")
    ap.add_argument("page_path")
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--shot", default="")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=1400)
    args = ap.parse_args()

    url = f"{args.base}/mirror/{args.task_id}/{args.page_path}"
    shot = args.shot or os.path.join("docs", args.task_id + "_render.png")

    chrome = find_chrome()
    failed, console = [], []
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=chrome, headless=True) if chrome \
            else pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": args.width, "height": args.height})
        pg.on("requestfailed", lambda r: failed.append({"url": r.url, "err": r.failure}))
        pg.on("response", lambda r: failed.append({"url": r.url, "status": r.status})
              if r.status >= 400 else None)
        pg.on("console", lambda m: console.append({"type": m.type, "text": m.text})
              if m.type == "error" else None)

        pg.goto(url, wait_until="load", timeout=45000)
        pg.wait_for_timeout(2500)

        info = pg.evaluate("""() => {
          const out = {};
          out.title = document.title;
          let rules = 0, sheets = [];
          for (const ss of document.styleSheets) {
            let n = -1;
            try { n = ss.cssRules ? ss.cssRules.length : -1; } catch (e) { n = -1; }
            if (n > 0) rules += n;
            sheets.push({ href: ss.href, rules: n });
          }
          out.sheets = sheets; out.totalRules = rules;
          const cs = (sel, prop) => { const e = document.querySelector(sel);
            return e ? getComputedStyle(e)[prop] : null; };
          out.bodyFont = cs('body', 'fontFamily');
          out.h1FontSize = cs('h1', 'fontSize');
          out.jquery = typeof window.jQuery;
          out.imgs = [...document.images].slice(0, 30)
            .map(i => ({ src: i.getAttribute('src'), nw: i.naturalWidth,
                         ok: i.complete && i.naturalWidth > 0 }));
          out.brokenImgs = out.imgs.filter(i => !i.ok).map(i => i.src);
          out.refs = performance.getEntriesByType('resource').length;
          return out;
        }""")

        os.makedirs(os.path.dirname(shot) or ".", exist_ok=True)
        pg.screenshot(path=shot, full_page=True)
        b.close()

    print("=== 渲染实测 ===")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print("\n=== 失败请求 ===")
    print("   （无）" if not failed else "")
    for f in failed:
        print("  ", f)
    print("\n=== console error ===")
    print("   （无）" if not console else "")
    for c in console[:15]:
        print("  ", c)
    print(f"\n截图: {shot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
