"""
编码修复的回归测试（不联网，跑得快）。

修复背景：镜像一律以 UTF-8 落盘，但磁盘上的编码声明没同步改写，
浏览器就会拿旧编码（gbk）去解 UTF-8 字节 → 整页乱码。
"""
import os
import sys

import httpx
import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.encoding_utils import (  # noqa: E402
    decode_body,
    detect_encoding,
    ensure_css_utf8_charset,
    normalize_html_charset,
    sniff_meta_charset,
    to_utf8_text,
)

GBK_TEXT = "\u4e2d\u6587\u65e0\u58f0\u660e\u4f46\u662fGBK"       # 中文无声明但是GBK
GBK_SITE = "\u4e2d\u6587\u6807\u9898\uff1a\u7f51\u9875\u955c\u50cf"  # 中文标题：网页镜像
BIG5_TEXT = "\u7e41\u9ad4\u4e2d\u6587\u6e2c\u8a66"                   # 繁體中文測試


# ---------------------------------------------------------------------------
# detect_encoding
# ---------------------------------------------------------------------------

def test_utf8_with_lying_latin1_header():
    """响应头谎报 latin-1、内容其实是 UTF-8 —— 最经典的乱码来源。"""
    raw = GBK_SITE.encode("utf-8")
    assert detect_encoding(raw, "iso-8859-1", None) == "utf-8"
    assert raw.decode(detect_encoding(raw, "iso-8859-1", None)) == GBK_SITE


def test_gbk_declared():
    raw = GBK_SITE.encode("gbk")
    enc = detect_encoding(raw, "gbk", None)
    assert raw.decode(enc) == GBK_SITE


def test_gbk_without_any_declaration():
    """没有任何声明时，不能让 charset_normalizer 把 GBK 误判成 Big5。"""
    raw = GBK_TEXT.encode("gbk")
    enc = detect_encoding(raw)
    assert raw.decode(enc) == GBK_TEXT


def test_big5_declared():
    raw = BIG5_TEXT.encode("big5")
    enc = detect_encoding(raw, "big5", None)
    assert raw.decode(enc) == BIG5_TEXT


def test_utf8_bom():
    raw = b"\xef\xbb\xbf" + GBK_SITE.encode("utf-8")
    enc = detect_encoding(raw)
    assert enc == "utf-8-sig"
    assert raw.decode(enc) == GBK_SITE


def test_pure_ascii_stays_utf8():
    assert detect_encoding(b"hello world") == "utf-8"


def test_numeric_entities_untouched():
    """纯 ASCII 的页面不该被改动编码。"""
    raw = b"<html><body>hi</body></html>"
    assert detect_encoding(raw) == "utf-8"


# ---------------------------------------------------------------------------
# decode_body（带响应头）
# ---------------------------------------------------------------------------

def _resp(content, content_type):
    return httpx.Response(200, content=content,
                          headers={"content-type": content_type})


def test_decode_body_gbk_header():
    r = _resp(GBK_SITE.encode("gbk"), "text/html; charset=gbk")
    assert decode_body(r) == GBK_SITE


def test_decode_body_wrong_header_utf8_content():
    r = _resp(GBK_SITE.encode("utf-8"), "text/html; charset=iso-8859-1")
    assert decode_body(r) == GBK_SITE


def test_decode_body_no_charset_gbk_content():
    r = _resp(GBK_TEXT.encode("gbk"), "text/html")
    assert decode_body(r) == GBK_TEXT


def test_sniff_meta_charset():
    raw = GBK_SITE.encode("gbk")
    assert sniff_meta_charset(b'<meta charset="gbk">' + raw) == "gbk"
    assert sniff_meta_charset(raw) is None


# ---------------------------------------------------------------------------
# normalize_html_charset
# ---------------------------------------------------------------------------

def _soup(html):
    return BeautifulSoup(html, "html.parser")


def test_normalize_rewrites_charset_attr():
    soup = _soup('<html><head><meta charset="gbk"><title>t</title></head></html>')
    normalize_html_charset(soup)
    assert 'charset="utf-8"' in str(soup)
    assert "gbk" not in str(soup)


def test_normalize_rewrites_http_equiv():
    soup = _soup('<html><head><meta http-equiv="Content-Type" '
                 'content="text/html; charset=gb2312"></head></html>')
    normalize_html_charset(soup)
    out = str(soup)
    assert "charset=utf-8" in out
    assert "gb2312" not in out


def test_normalize_injects_when_missing():
    """没有任何声明时必须补一个，否则中文 Windows 浏览器按 GBK 猜 → 乱码。"""
    soup = _soup("<html><head><title>t</title></head><body>x</body></html>")
    normalize_html_charset(soup)
    metas = soup.find_all("meta", attrs={"charset": "utf-8"})
    assert len(metas) == 1
    assert metas[0].parent.name == "head"


def test_normalize_injects_into_headless_doc():
    soup = _soup("<body>x</body>")
    normalize_html_charset(soup)
    assert soup.find("meta", attrs={"charset": "utf-8"}) is not None


# ---------------------------------------------------------------------------
# CSS / 文本资源
# ---------------------------------------------------------------------------

def test_css_charset_rewritten():
    css = '@charset "gbk";\n.box{content:"\u4e2d\u6587"}'
    out = ensure_css_utf8_charset(css)
    assert out.startswith('@charset "utf-8";')
    assert "\u4e2d\u6587" in out


def test_css_without_charset_untouched():
    css = ".box{color:red}"
    assert ensure_css_utf8_charset(css) == css


def test_to_utf8_text_converts_gbk_js():
    src = 'var msg = "\u4e2d\u6587\u811a\u672c";\n'
    raw = src.encode("gbk")
    out = to_utf8_text(raw, "a/b/app.js", "application/javascript")
    assert out.decode("utf-8") == src


def test_to_utf8_text_keeps_utf8_bytes_identical():
    raw = "var msg = \"\u4e2d\u6587\";".encode("utf-8")
    assert to_utf8_text(raw, "app.js", "application/javascript") is raw


def test_to_utf8_text_leaves_binary_alone():
    raw = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    assert to_utf8_text(raw, "logo.png", "image/png") == raw


def test_to_utf8_text_leaves_nul_containing_file_alone():
    raw = b"var x = 1;\x00\x01\x02"
    assert to_utf8_text(raw, "weird.js", "text/javascript") == raw


def test_to_utf8_text_rewrites_xml_declaration():
    src = "<?xml version=\"1.0\" encoding=\"gbk\"?><root>\u4e2d\u6587</root>"
    out = to_utf8_text(src.encode("gbk"), "a.xml", "text/xml")
    text = out.decode("utf-8")
    assert 'encoding="utf-8"' in text
    assert "\u4e2d\u6587" in text


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
