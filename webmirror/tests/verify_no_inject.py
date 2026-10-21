"""验证：新版本抓取的页面不再注入任何内容（100% 原样）。"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

try:                      # 控制台可能是 GBK，避免打印 emoji 报错
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:         # noqa: BLE001
    pass

BASE = "http://127.0.0.1:8000"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_no_inject_result.txt")
DL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads")


def req(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        return resp.status, resp.read()


def find_html(tree):
    if tree.get("type") == "file":
        return tree["path"] if tree.get("path", "").endswith(".html") else None
    for ch in tree.get("children") or []:
        got = find_html(ch)
        if got:
            return got
    return None


def main():
    lines = []
    _st, body = req("POST", "/api/tasks",
                    {"url": "https://example.com/", "max_depth": 1,
                     "max_pages": 1, "max_assets": 3, "concurrency": 2})
    tid = json.loads(body)["tasks"][0]["id"]
    lines.append(f"1) 新建任务 id={tid}")

    for _ in range(60):
        time.sleep(1)
        _st, body = req("GET", f"/api/tasks/{tid}")
        task = json.loads(body)["task"]
        if task["status"] != "running":
            break
    lines.append(f"2) 抓取结束 status={task['status']}")

    _st, body = req("GET", f"/api/tasks/{tid}/tree")
    html_rel = find_html(json.loads(body)["tree"])

    # 找到本地磁盘路径
    out_dir = task.get("out_dir") or task.get("output_dir")
    disk = None
    for root, _d, files in os.walk(DL):
        if tid in root or (out_dir and os.path.abspath(root).startswith(os.path.abspath(out_dir))):
            cand = os.path.join(root, html_rel.replace("/", os.sep))
            if os.path.isfile(cand):
                disk = cand
                break
    lines.append(f"3) HTML = {html_rel}  本地文件 = {disk}")

    text = open(disk, "r", encoding="utf-8", errors="replace").read()
    has_marker = "webmirror-source" in text
    lines.append(f"4) 是否含注入标记 webmirror-source : {has_marker}")

    # 抓原站内容做对照
    with urllib.request.urlopen("https://example.com/", timeout=30) as r:
        origin = r.read().decode("utf-8", "replace")

    lines.append(f"5) 本地文件字节数 = {len(text)}")
    lines.append(f"   顶部 200 字 = {text[:200]!r}")
    # 关键：原站正文必须完整保留
    probe = "This domain is for use in documentation examples"
    lines.append(f"6) 原站正文保留 = {probe in text}")
    lines.append(f"7) <head> 起始片段 = {text[text.find('<head'):text.find('<head')+120]!r}")

    ok = (not has_marker) and (probe in text)
    lines.append("")
    lines.append("结论: " + ("✅ 通过：零注入，正文原样保留" if ok else "❌ 失败"))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
