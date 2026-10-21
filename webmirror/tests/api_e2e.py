"""完整 API 链路验证：创建任务 -> 抓 GBK 站点 -> 预览接口 -> 检查编码 -> 清理。"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_e2e_result.txt")


def req(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        body = resp.read()
        return resp.status, dict(resp.headers), body


def find_html(tree):
    """在文件树里找第一个 .html 文件。"""
    if tree.get("type") == "file":
        return tree["path"] if tree.get("path", "").endswith(".html") else None
    for ch in tree.get("children") or []:
        got = find_html(ch)
        if got:
            return got
    return None


def main():
    lines = []
    tid = None
    try:
        st, _h, body = req("POST", "/api/tasks",
                           {"url": "http://www.cnr.cn/", "max_depth": 1,
                            "max_pages": 2, "max_assets": 5, "concurrency": 3})
        info = json.loads(body)
        tid = info["tasks"][0]["id"]
        lines.append(f"1) 创建任务 OK id={tid}")

        for _ in range(90):
            time.sleep(1)
            st, _h, body = req("GET", f"/api/tasks/{tid}")
            task = json.loads(body)["task"]
            if task["status"] != "running":
                break
        lines.append(f"2) 任务结束 status={task['status']} "
                     f"页面={task['stats'].get('pages_ok')} "
                     f"资源={task['stats'].get('assets_ok')}")

        st, _h, body = req("GET", f"/api/tasks/{tid}/tree")
        tree = json.loads(body)["tree"]
        html_path = find_html(tree)
        lines.append(f"3) 文件树 OK，首个 HTML = {html_path}")

        # 预览接口（iframe 用的就是它）
        q = urllib.parse.urlencode({"path": html_path})
        st, headers, body = req("GET", f"/api/tasks/{tid}/serve?{q}")
        ctype = headers.get("Content-Type") or headers.get("content-type")
        text = body.decode("utf-8", "replace")
        hanzi = [c for c in text if "\u4e00" <= c <= "\u9fff"]
        ok_hdr = "charset=utf-8" in (ctype or "")
        ok_body = "\ufffd" not in text and len(hanzi) > 20
        lines.append(f"4) /serve HTTP {st}\n   Content-Type = {ctype}\n"
                     f"   带 charset=utf-8 = {ok_hdr}\n"
                     f"   UTF-8 解码正常(无U+FFFD, 汉字{len(hanzi)}个) = {ok_body}\n"
                     f"   正文片段: {text[text.find('<body'):text.find('<body') + 120]!r}")

        # 文本预览接口
        q2 = urllib.parse.urlencode({"path": html_path, "as_text": "true"})
        st2, _h2, body2 = req("GET", f"/api/tasks/{tid}/raw?{q2}")
        j = json.loads(body2)
        ok_raw = "\ufffd" not in j["text"]
        lines.append(f"5) /raw(as_text) OK={ok_raw} 长度={j['size']}")

        lines.append("")
        lines.append("结论: " + ("全部通过" if (ok_hdr and ok_body and ok_raw)
                                 else "存在失败"))
    except Exception as exc:                          # noqa: BLE001
        lines.append(f"异常: {type(exc).__name__}: {exc}")
    finally:
        if tid:
            try:
                req("DELETE", f"/api/tasks/{tid}?remove_files=true")
                lines.append(f"6) 已清理任务 {tid}")
            except Exception as exc:                  # noqa: BLE001
                lines.append(f"清理失败: {exc}")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("done ->", OUT)


if __name__ == "__main__":
    main()
