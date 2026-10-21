"""最小化 HTML 改写（app/minimal_html.py）单元测试。

重点保证：**不该动的字节一个都不能动**——属性顺序、引号风格、void 元素
写法、<script>/注释内容都要原样保留；只有链接属性值与字符集声明允许改写。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.minimal_html import rewrite_html  # noqa: E402


def _map_factory(mapping):
    def attr_map(tag, attr, value, attrs):
        return mapping.get((tag, attr))
    return attr_map


# ---------------------------------------------------------------------------
# 1. 不改写时，输出必须与输入逐字节一致
# ---------------------------------------------------------------------------

def test_untouched_bytes_identical():
    html = (
        "<!DOCTYPE html>\n"
        "<html>\n<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<meta http-equiv="Cache-Control" content="no-transform">\n'
        "<title>t</title>\n"
        "</head>\n<body>\n"
        '<img src="a.png" alt="x">\n<br>\n<input type="text">\n<hr>\n'
        "</body>\n</html>\n"
    )
    out = rewrite_html(html, attr_map=_map_factory({}))
    assert out == html, "不应有任何改动"


def test_attribute_order_and_quotes_preserved():
    html = "<head><meta charset='utf-8'></head><body><a href='/x' class=\"y\">go</a></body>"
    out = rewrite_html(html, attr_map=_map_factory({}))
    assert out == html
    assert "href='/x'" in out        # 单引号保留
    assert 'class="y"' in out        # 双引号保留


def test_void_elements_no_self_closing_slash():
    html = "<head><meta charset='utf-8'></head><body><br><img src='a.png'><hr></body>"
    out = rewrite_html(html, attr_map=_map_factory({}))
    assert "<br>" in out and "<br/>" not in out
    assert "<hr>" in out and "<hr/>" not in out
    assert "<img src='a.png'>" in out


# ---------------------------------------------------------------------------
# 2. 只改该改的
# ---------------------------------------------------------------------------

def test_link_rewritten_only():
    html = (
        "<head><meta charset='utf-8'></head><body>"
        '<a href="/docs/" class="nav">go</a>'
        "</body>"
    )
    out = rewrite_html(html, attr_map=_map_factory({("a", "href"): "docs/index.html"}))
    assert 'href="docs/index.html"' in out
    assert 'class="nav"' in out
    assert out.count("<a ") == 1


def test_script_and_comment_untouched():
    html = (
        "<head><meta charset='utf-8'></head><body>"
        '<script>var s = \'<a href="/docs/">x</a>\';</script>'
        '<!-- <a href="/docs/">c</a> -->'
        '<a href="/docs/">real</a>'
        "</body>"
    )
    out = rewrite_html(html, attr_map=_map_factory({("a", "href"): "docs/index.html"}))
    assert '<a href="/docs/">x</a>' in out        # script 内保留
    assert '<!-- <a href="/docs/">c</a> -->' in out  # 注释内保留
    assert 'href="docs/index.html"' in out          # 真实链接被改写


def test_srcset_rewritten():
    html = "<head><meta charset='utf-8'></head><body><img srcset='/a.png 1x, /b.png 2x'></body>"
    out = rewrite_html(
        html,
        attr_map=_map_factory({("img", "srcset"): "a.png 1x, b.png 2x"}),
    )
    assert "srcset='a.png 1x, b.png 2x'" in out     # 引号风格沿用原文单引号


def test_unquoted_attr_rewritten_and_style_preserved():
    html = (
        "<head><meta charset=utf-8></head><body>"
        "<script src=/s.js></script>"
        "<img src=a.png>"
        "</body>"
    )
    out = rewrite_html(
        html,
        attr_map=_map_factory({("script", "src"): "s.js", ("img", "src"): "img/a.png"}),
    )
    assert "<script src=s.js>" in out      # 无引号仍无引号
    assert "<img src=img/a.png>" in out
    assert "<meta charset=utf-8>" in out    # 未改动的原样保留


def test_unquoted_attr_value_with_space_gets_quoted():
    html = "<head><meta charset=utf-8></head><body><a href=/x>go</a></body>"
    out = rewrite_html(
        html,
        attr_map=_map_factory({("a", "href"): "a b/index.html"}),
    )
    assert 'href="a b/index.html"' in out


def test_data_url_and_hash_not_touched():
    html = (
        "<head><meta charset='utf-8'></head><body>"
        "<link rel=icon href=data:,>"
        '<a href="#top">x</a>'
        "</body>"
    )
    out = rewrite_html(html, attr_map=_map_factory({}))
    assert out == html


def test_style_block_and_attribute():
    html = (
        "<head><meta charset='utf-8'><style>body{background:url('bg.png')}</style></head>"
        '<body><div style="background:url(i.png)">x</div></body>'
    )

    def style_map(css):
        return css.replace("bg.png", "img/bg.png").replace("i.png", "img/i.png")

    out = rewrite_html(html, attr_map=_map_factory({}), style_map=style_map)
    assert "url('img/bg.png')" in out
    assert 'style="background:url(img/i.png)"' in out


# ---------------------------------------------------------------------------
# 3. 字符集声明
# ---------------------------------------------------------------------------

def test_charset_gbk_rewritten():
    html = "<head><meta charset='gbk'><title>x</title></head><body>中文</body>"
    out = rewrite_html(html, attr_map=_map_factory({}))
    assert "charset='utf-8'" in out
    assert "gbk" not in out


def test_charset_http_equiv_rewritten():
    html = (
        "<head><meta http-equiv='Content-Type' content='text/html; charset=gb2312'>"
        "</head><body>x</body>"
    )
    out = rewrite_html(html, attr_map=_map_factory({}))
    assert "charset=utf-8" in out
    assert "gb2312" not in out
    assert "http-equiv='Content-Type'" in out     # 其余属性不动


def test_charset_inserted_when_missing():
    html = "<html><head><title>x</title></head><body>中文</body></html>"
    out = rewrite_html(html, attr_map=_map_factory({}))
    assert '<meta charset="utf-8"/>' in out
    # 插到 <head> 之后
    assert out.index("utf-8") < out.index("<title>")


def test_no_insert_when_declared():
    html = "<head><meta charset='utf-8'></head><body>x</body>"
    out = rewrite_html(html, attr_map=_map_factory({}))
    assert out == html


def test_ensure_charset_disabled():
    html = "<head><title>x</title></head><body>x</body>"
    out = rewrite_html(html, attr_map=_map_factory({}), ensure_charset=False)
    assert out == html
