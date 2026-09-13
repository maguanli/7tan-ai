# -*- coding: utf-8 -*-
"""读取微信后台 Cookie 并获取草稿全文"""
import base64
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(r"D:\7tan\7tanAI")
COOKIE_FILE = ROOT / "data" / "browser_cookies.json"
TOKEN = "1424585344"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

def load_cookies():
    """解析 browser_cookies.json -> {name: value}"""
    data = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
    cookies = {}
    for c in data.get("cookies", []):
        raw = c.get("raw", "")
        try:
            raw_bytes = base64.b64decode(raw)
        except Exception:
            continue
        text = raw_bytes.decode("utf-8", "ignore")
        # Set-Cookie 第一行: name=value
        m = re.match(r"([^=;=\s]+)=([^;]*)", text)
        if m:
            cookies[m.group(1)] = m.group(2)
    return cookies

def main():
    cookies = load_cookies()
    print(f"解析到 cookie 数量: {len(cookies)}")
    print("关键 cookie:", {k: (v[:10] + '...' if len(v) > 10 else v) for k, v in cookies.items() if k in ('slave_sid', 'data_ticket', 'slave_user')})

    if not cookies:
        print("❌ 无 cookie，无法继续")
        return

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": "https://mp.weixin.qq.com/"})
    s.cookies.update(cookies)

    # 1. 获取草稿列表（type=77 草稿箱）
    list_url = f"https://mp.weixin.qq.com/cgi-bin/appmsg?begin=0&count=10&type=77&action=list_card&token={TOKEN}&lang=zh_CN"
    try:
        r = s.get(list_url, timeout=30)
        print(f"草稿列表 HTTP {r.status_code}, 长度 {len(r.text)}")
        if r.status_code != 200:
            print("响应头:", dict(r.headers))
            return
        # 提取 appmsgid
        ids = re.findall(r'"appmsgid":\s*(\d+)', r.text)
        titles = re.findall(r'"title":\s*"([^"]{5,80})"', r.text)
        print("appmsgid 列表:", ids[:10])
        print("标题列表:", titles[:10])
        if not ids:
            # 可能被重定向到登录页
            if "login" in r.url or "请先登录" in r.text[:500]:
                print("❌ 被重定向到登录页，cookie 失效")
            else:
                print("⚠️ 未提取到 appmsgid，页面片段:", r.text[:300])
            return
        appmsgid = ids[0]
        print(f"\n使用草稿 appmsgid: {appmsgid}")

        # 2. 获取草稿编辑页
        edit_url = (f"https://mp.weixin.qq.com/cgi-bin/appmsg"
                    f"?t=media/appmsg_edit&action=edit&type=77"
                    f"&appmsgid={appmsgid}&token={TOKEN}&lang=zh_CN")
        r2 = s.get(edit_url, timeout=30)
        print(f"编辑页 HTTP {r2.status_code}, 长度 {len(r2.text)}")
        if r2.status_code != 200:
            print("❌ 编辑页请求失败")
            return
        # 提取正文 HTML（content 字段）
        m = re.search(r'"content":\s*"((?:[^"\\]|\\.)*)"', r2.text)
        if m:
            content = m.group(1).encode("utf-8").decode("unicode_escape", "ignore")
            # 简单反转义
            content = content.replace('\\"', '"').replace("\\n", "\n")
            print(f"\n✅ 提取到正文，长度 {len(content)} 字符")
            out = ROOT / "data" / "gzh_draft_content.html"
            out.write_text(content, encoding="utf-8")
            print(f"已保存到 {out}")
            # 去掉标签显示纯文本预览
            text_only = re.sub(r"<[^>]+>", " ", content)
            text_only = re.sub(r"\s+", " ", text_only).strip()
            print("\n=== 正文纯文本预览（前1200字）===")
            print(text_only[:1200])
        else:
            # 尝试其他字段
            m2 = re.search(r'"digest":\s*"([^"]*)"', r2.text)
            print("⚠️ 未提取到 content，digest:", m2.group(1) if m2 else None)
            print("页面片段:", r2.text[:500])
    except Exception as e:
        print(f"❌ 异常: {e}")

if __name__ == "__main__":
    main()
