"""静态资源跨主机抓取范围（asset_scope）与主域判定测试。

背景：像 quhao.293.net 这类站点，CSS/JS/图片托管在 i.293.net、www.293.net，
旧版 only 抓「同主机」导致 assets_ok = 0，镜像页面无样式。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crawler import CrawlConfig, Mirror, base_domain  # noqa: E402


def _mirror(start_url: str, **kw) -> Mirror:
    cfg = CrawlConfig(start_url=start_url, **kw)
    return Mirror(cfg)


def test_base_domain():
    cases = {
        "quhao.293.net": "293.net",
        "i.293.net": "293.net",
        "www.293.net": "293.net",
        "293.net": "293.net",
        "a.b.com.cn": "b.com.cn",
        "news.sina.com.cn": "sina.com.cn",
        "x.co.uk": "x.co.uk",
        "a.b.co.uk": "b.co.uk",
        "example.com": "example.com",
        "127.0.0.1": "127.0.0.1",
        "localhost": "localhost",
    }
    for host, want in cases.items():
        got = base_domain(host)
        assert got == want, f"base_domain({host!r}) = {got!r}, want {want!r}"
    print(f"[OK] base_domain {len(cases)} 例")


def test_scope_same_host():
    m = _mirror("http://quhao.293.net/", same_domain=True, asset_scope="same_host")
    assert m._is_allowed("http://quhao.293.net/x.html", "page")
    assert m._is_allowed("http://quhao.293.net/style/a.css", "asset")
    # 姊妹子域属于同主域，但 same_host 下应被拒绝
    assert not m._is_allowed("http://i.293.net/2018/style.css", "asset")
    # 页面依然被限制
    assert not m._is_allowed("http://i.293.net/", "page")
    print("[OK] same_host")


def test_scope_same_site_default():
    m = _mirror("http://quhao.293.net/", same_domain=True)
    assert m.cfg.asset_scope == "same_site"          # 新默认值
    assert m._is_allowed("http://quhao.293.net/x.html", "page")
    # 关键修复点：姊妹子域的静态资源现在允许抓取
    assert m._is_allowed("http://i.293.net/2018/style.css", "asset")
    assert m._is_allowed("http://i.293.net/fav/quhao.ico", "asset")
    assert m._is_allowed("http://www.293.net/images/logo.gif", "asset")
    # 但页面仍然不能跳到其它主机
    assert not m._is_allowed("http://i.293.net/", "page")
    # 完全不同的主域（第三方 CDN）仍不允许
    assert not m._is_allowed("http://apps.bdimg.com/libs/jquery.min.js", "asset")
    print("[OK] same_site（默认）")


def test_scope_any():
    m = _mirror("http://quhao.293.net/", same_domain=True, asset_scope="any")
    assert m._is_allowed("http://apps.bdimg.com/libs/jquery.min.js", "asset")
    assert m._is_allowed("http://cdn.example.org/a/b.css", "asset")
    # 页面依然限制在同站
    assert not m._is_allowed("http://apps.bdimg.com/", "page")
    print("[OK] any")


def test_same_domain_off():
    m = _mirror("http://quhao.293.net/", same_domain=False)
    assert m._is_allowed("http://anywhere.example/x.css", "asset")
    assert m._is_allowed("http://anywhere.example/page", "page")
    print("[OK] same_domain=False（不限制）")


def test_blocked_patterns_still_apply():
    m = _mirror("http://quhao.293.net/", asset_scope="any",
                exclude_patterns=[r"/ads/"])
    assert not m._is_allowed("http://cdn.example.org/ads/a.js", "asset")
    assert m._is_allowed("http://cdn.example.org/ok/a.js", "asset")
    print("[OK] 排除规则对资源同样生效")


def test_map_to_local_cross_host():
    """跨主机资源应改写成带主机目录的相对路径（离线可解析）。"""
    m = _mirror("http://quhao.293.net/", asset_scope="same_site", with_host_dir=True)
    rel = m._map_to_local("//i.293.net/2018/style.css",
                          "http://quhao.293.net/index.html", "quhao.293.net", "asset")
    assert rel == "../i.293.net/2018/style.css", rel
    # 同一 host 下的相对路径
    # 相对链接基于所在页面解析：/a/b.html 里的 style/m.css -> /a/style/m.css
    rel2 = m._map_to_local("style/m.css",
                           "http://quhao.293.net/a/b.html", "quhao.293.net/a", "asset")
    assert rel2 == "style/m.css", rel2
    print("[OK] 跨主机路径改写")


if __name__ == "__main__":
    for fn in (test_base_domain, test_scope_same_host, test_scope_same_site_default,
               test_scope_any, test_same_domain_off, test_blocked_patterns_still_apply,
               test_map_to_local_cross_host):
        fn()
    print("\n全部通过")
