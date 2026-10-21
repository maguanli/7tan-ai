"""路径映射单元测试：python tests/test_paths.py"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.paths import guess_ext_by_content_type, sanitize_segment, url_to_relpath  # noqa: E402

CASES = [
    # (url, 期望相对路径, kwargs)
    ("https://example.com/", "example.com/index.html", {}),
    ("https://example.com", "example.com/index.html", {}),
    ("https://example.com/index.html", "example.com/index.html", {}),
    ("https://example.com/docs/guide.html", "example.com/docs/guide.html", {}),
    ("https://example.com/docs/", "example.com/docs/index.html", {}),
    ("https://example.com/a/b/c/", "example.com/a/b/c/index.html", {}),
    ("https://example.com/img/logo.png", "example.com/img/logo.png", {}),
    ("https://example.com/about", "example.com/about/index.html", {}),
    ("https://example.com/about", "example.com/about.html", {"extensionless": "html"}),
    ("https://example.com/list?page=2", "example.com/list/@page=2/index.html", {}),
    ("https://example.com/a/b?x=1&y=2", "example.com/a/b/@x=1@y=2/index.html", {}),
    ("https://example.com/i.php?id=9", "example.com/i@id=9.php", {}),
    ("https://example.com/list?page=2", "example.com/list/index.html", {"param_mode": "ignore"}),
    ("http://example.com:8080/x.html", "example.com_8080/x.html", {}),
    ("https://example.com/x.html", "x.html", {"with_host": False}),
    ("https://example.com/子目录/中文页.html", "example.com/子目录/中文页.html", {}),
    ("https://example.com/a%20b/c.html", "example.com/a b/c.html", {}),
    ("https://example.com/a%2Fb/c.html", "example.com/a_b/c.html", {}),
    ("https://example.com/a/../../etc/passwd", "example.com/a/__/__/etc/passwd/index.html", {}),
]

UNIQUE_URLS = [
    "https://example.com/a",
    "https://example.com/a?x=1",
    "https://example.com/a.html",
    "https://example.com/b/a",
    "https://example.com/docs/x",
    "https://example.com/docs/x.html",
    "https://example.com/docs/x?y=2",
    "https://example.com/docs/x/y/z",
]


def main() -> int:
    ok = fail = 0

    for url, expect, kw in CASES:
        got = url_to_relpath(url, **kw)
        good = got == expect
        print(("[OK] " if good else "[FAIL] ") + url)
        if not good:
            print(f"       期望: {expect}")
            print(f"       实际: {got}")
        ok, fail = (ok + 1, fail) if good else (ok, fail + 1)

    # hash 模式只校验前缀
    got = url_to_relpath("https://example.com/list?page=2", param_mode="hash")
    good = got.startswith("example.com/list/@q=") and got.endswith("/index.html")
    print(("[OK] " if good else "[FAIL] ") + f"hash 模式: {got}")
    ok, fail = (ok + 1, fail) if good else (ok, fail + 1)

    # 唯一性：不同 URL 必须落到不同文件
    paths = [url_to_relpath(u) for u in UNIQUE_URLS]
    uniq = len(set(paths)) == len(paths)
    print(("[OK] " if uniq else "[FAIL] ") + f"唯一性: {len(set(paths))}/{len(paths)}")
    if not uniq:
        from collections import Counter
        for p, c in Counter(paths).items():
            if c > 1:
                print("       冲突路径:", p)
    ok, fail = (ok + 1, fail) if uniq else (ok, fail + 1)

    # 净化规则
    checks = [
        (sanitize_segment('a<b>c:d"e|f?g*h'), "a_b_c_d_e_f_g_h", "非法字符"),
        (sanitize_segment(".."), "__", ".. 净化"),
        (sanitize_segment("..."), "_", "全点号净化"),
        (sanitize_segment("CON"), "_CON", "Windows 保留名"),
        (sanitize_segment("  tail.  "), "tail", "首尾空格与点"),
    ]
    for got_v, exp_v, name in checks:
        good = got_v == exp_v
        print(("[OK] " if good else "[FAIL] ") + f"净化-{name}: {got_v!r}")
        ok, fail = (ok + 1, fail) if good else (ok, fail + 1)

    for ct, ext in [("image/jpeg", ".jpg"), ("text/html; charset=utf-8", ".html"),
                    ("font/woff2", ".woff2"), ("video/mp4", ".mp4")]:
        got_v = guess_ext_by_content_type(ct)
        good = got_v == ext
        print(("[OK] " if good else "[FAIL] ") + f"mime {ct} -> {got_v}")
        ok, fail = (ok + 1, fail) if good else (ok, fail + 1)

    print(f"\n结果: {ok} 通过 / {fail} 失败")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
