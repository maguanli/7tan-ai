# -*- coding: utf-8 -*-
"""回归测试：补抓脚本必须处理 CSS 内的「相对路径」url()/@import。

背景 bug：旧版 rewrite_link 只处理「绝对 / 协议相对 / 根相对」链接，
相对 url() 直接 return None，导致 CSS 里的相对图片被静默漏抓
（实例：anquanqi.293.net 的 style.css 里 url(../images/heart.png)、url(bg2_03.gif)）。
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repair_assets import Repairer          # noqa: E402


def _build_tree(tmp: str) -> str:
    """构造：页面在 site.example，CSS 在兄弟域 assets.site.example（同主域）。"""
    task = tmp
    os.makedirs(os.path.join(task, "site.example"), exist_ok=True)
    os.makedirs(os.path.join(task, "assets.site.example", "css"), exist_ok=True)
    os.makedirs(os.path.join(task, "assets.site.example", "img"), exist_ok=True)

    with open(os.path.join(task, "site.example", "index.html"), "w", encoding="utf-8") as f:
        f.write('<!DOCTYPE html><html><head>'
                '<link rel="stylesheet" href="http://assets.site.example/css/m.css">'
                '</head><body>hi</body></html>')

    with open(os.path.join(task, "_mirror_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"start_url": "http://site.example/",
                   "files": [{"path": "site.example/index.html", "url": "http://site.example/"}]}, f)

    # 已存在的 CSS：含相对 url()（../img/hero.png）与 @import 相对路径
    with open(os.path.join(task, "assets.site.example", "css", "m.css"), "w", encoding="utf-8") as f:
        f.write("body{background:url(../img/hero.png) no-repeat;}\n"
                "@import 'sub/extra.css';\n"
                ".a{background:url('/images/root.png')}\n")
    return task


def test_css_relative_url_is_queued():
    """相对 url() 必须被识别为待抓资源。"""
    with tempfile.TemporaryDirectory() as tmp:
        task = _build_tree(tmp)
        r = Repairer(task, "same_site", dry_run=True)
        r.scan_css()
        urls = set(r.todo.values())
        assert "http://assets.site.example/img/hero.png" in urls, urls
        assert "http://assets.site.example/css/sub/extra.css" in urls, urls
        assert "http://assets.site.example/images/root.png" in urls, urls


def test_css_relative_path_not_rewritten_when_same_location():
    """相对 url()/@import 解析后指向原位置 -> 原样不动；
    根相对链接则必须改写成相对路径（否则会指向镜像站根目录）。"""
    with tempfile.TemporaryDirectory() as tmp:
        task = _build_tree(tmp)
        r = Repairer(task, "same_site", dry_run=False)
        css = os.path.join(task, "assets.site.example", "css", "m.css")
        r.scan_css()
        after = open(css, encoding="utf-8").read()
        # 相对路径：原地不动
        assert "url(../img/hero.png)" in after, after
        assert "@import 'sub/extra.css'" in after, after
        # 根相对：必须本地化
        assert "url('/images/root.png')" not in after, after
        assert "url('../images/root.png')" in after, after


def test_html_relative_link_still_skipped():
    """HTML 里的相对链接仍应跳过（抓取阶段已处理，不能当成跨主机资源）。"""
    with tempfile.TemporaryDirectory() as tmp:
        task = _build_tree(tmp)
        r = Repairer(task, "same_site", dry_run=True)
        r.scan_html()
        assert not any(k.startswith("site.example/site.example") for k in r.todo), r.todo
