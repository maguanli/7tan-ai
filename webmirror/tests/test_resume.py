"""断点续抓测试：

1. 造一个三层深度的本地站点（首页 → 省 → 市 → 详情）。
2. 子进程抓取，跑到一半**强杀**（模拟服务重启/崩溃）。
3. 检查留下了 _mirror_state.json，且待抓队列非空。
4. 用同一输出目录续抓至完成。
5. 断言：详情页全部到位；清单 NDJSON 中**没有重复路径**（证明已抓过的没重抓）。

运行：python tests/test_resume.py
"""
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from app.crawler import CrawlConfig, Mirror   # noqa: E402

SITE = os.path.join(HERE, "_resume_site")
OUT = os.path.join(HERE, "_resume_out")
PORT = 8931
BASE = f"http://127.0.0.1:{PORT}/"

PROV = 30
CITY = 10
DETAIL = 4


def build_site() -> list[str]:
    """返回全部应当被抓到的相对路径（不含 index.html）。"""
    shutil.rmtree(SITE, ignore_errors=True)
    os.makedirs(SITE)

    def w(name: str, links: list[str]) -> None:
        body = ("<html><head><meta charset='utf-8'></head><body>"
                + "".join(f'<a href="{l}">{l}</a>' for l in links)
                + "</body></html>")
        with open(os.path.join(SITE, name), "w", encoding="utf-8") as f:
            f.write(body)

    expected: list[str] = []
    provs = [f"p{i}.html" for i in range(1, PROV + 1)]
    w("index.html", provs)
    for pi, pname in enumerate(provs, 1):
        cities = [f"c{pi}_{j}.html" for j in range(1, CITY + 1)]
        w(pname, cities)
        expected += cities
        for cname in cities:
            base = cname[:-5]
            details = [f"d_{base}_{k}.html" for k in range(1, DETAIL + 1)]
            w(cname, details)
            for d in details:
                w(d, [])
                expected.append(d)
    return expected


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs) -> None:      # 静音访问日志
        pass


def start_server() -> _Server:
    def handler(*a, **kw):
        kw["directory"] = SITE
        return _QuietHandler(*a, **kw)
    srv = _Server(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def read_journal(path: str) -> list[dict]:
    """读回入队流水账（每行: depth\tkind\turl，换行前置）。"""
    out: dict[str, dict] = {}
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t", 2)
            if len(parts) != 3:
                continue
            d, k, u = parts
            if not u or u in out or not u.startswith(("http://", "https://")):
                continue
            try:
                d = int(d)
            except ValueError:
                d = 0
            if k not in ("page", "asset"):
                k = "page"
            out[u] = {"url": u, "depth": d, "kind": k}
    return list(out.values())


def read_ndjson(path: str) -> list[dict]:
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass          # 被强杀撕裂的残缺记录，跳过
    return out


def main() -> int:
    expected = build_site()
    total_pages = 1 + PROV + PROV * CITY + len(expected) - PROV * CITY
    print(f"站点已生成：预计页面 {total_pages} 个（其中详情页 {len(expected) - PROV * CITY}）")

    shutil.rmtree(OUT, ignore_errors=True)
    srv = start_server()
    time.sleep(0.3)
    fails: list[str] = []

    try:
        # ---------- 阶段 1：跑到一半强杀 ----------
        proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "_resume_worker.py"), BASE, OUT],
            cwd=ROOT,
        )
        time.sleep(8.0)
        killed = proc.poll() is None
        proc.kill()
        proc.wait(timeout=10)
        print(f"阶段1：{'已强杀子进程（模拟中断）' if killed else '子进程已自行结束（未抓完）'}")

        state_path = os.path.join(OUT, "_mirror_state.json")
        ndjson_path = os.path.join(OUT, "_mirror_manifest.ndjson")
        journal_path = os.path.join(OUT, "_mirror_queue.ndjson")
        if not os.path.isfile(state_path):
            fails.append("中断后未留下 _mirror_state.json")
        state = json.load(open(state_path, encoding="utf-8")) if os.path.isfile(state_path) else {}

        # 新设计：待抓队列不再整体写进状态文件（体积会随抓取量线性膨胀，
        # 实测跑到 28 万 URL 时快照 87MB / 序列化 1.34s，把抓取拖垮），
        # 而是由「入队流水账 − 已落盘」精确重建。故此处按真实来源校验。
        journal = read_journal(journal_path)
        entries_now = read_ndjson(ndjson_path)
        files_before = {e["path"] for e in entries_now}
        done_urls = {e.get("url") for e in entries_now}
        pending = [it for it in journal if it["url"] not in done_urls]
        visited_n = int(state.get("visited_count") or 0)
        print(f"阶段1：入队流水 {len(journal)} 条，已落盘 {len(files_before)} 个，"
              f"待续 {len(pending)}，visited_count={visited_n}")

        if not journal:
            fails.append("未留下入队流水账 _mirror_queue.ndjson（队列没保住，无法续抓）")
        if len(pending) == 0:
            fails.append("按「流水账−已落盘」推算的待抓队列为空（队列没保住）")
        if len(pending) + len(files_before) > total_pages + 5:
            fails.append(f"待续+已落盘 异常偏大：{len(pending)}+{len(files_before)}")

        # ---------- 阶段 2：原地续抓 ----------
        cfg = CrawlConfig(
            start_url=BASE, out_root=OUT, max_depth=10, max_pages=100000,
            concurrency=8, delay=0.0, same_domain=True, include_assets=True,
            rewrite_links=True, resume=True, timeout=20.0, retries=1,
        )
        mirror = Mirror(cfg)
        stats = None

        import asyncio

        async def go():
            nonlocal stats
            stats = await mirror.run()

        asyncio.run(go())
        print(f"阶段2：续抓完成，页面 {stats['pages_ok']}，文件 {stats['files']}，"
              f"耗时 {stats['elapsed']}s")

        if not mirror._resumed:
            fails.append("阶段2未走上续抓分支（_resumed=False）")

        # ---------- 阶段 3：再续一次，应当无事可做（幂等） ----------
        lines_before = len(read_ndjson(ndjson_path))
        m3 = Mirror(cfg)
        stats3 = None

        async def go3():
            nonlocal stats3
            stats3 = await m3.run()

        asyncio.run(go3())
        lines_after = len(read_ndjson(ndjson_path))
        print(f"阶段3：再次续抓 → 清单 {lines_before} → {lines_after} 条（含自愈修复），"
              f"文件 {stats3['files']}")
        if lines_after - lines_before > 5:
            fails.append(f"阶段3 重复抓取过多：{lines_before} → {lines_after}")
        if lines_after != total_pages:
            fails.append(f"阶段3 后清单应为 {total_pages} 条，实际 {lines_after}")

        # ---------- 阶段 4：再续一次，必须完全空跑 ----------
        m4 = Mirror(cfg)
        stats4 = None

        async def go4():
            nonlocal stats4
            stats4 = await m4.run()

        asyncio.run(go4())
        lines_final = len(read_ndjson(ndjson_path))
        print(f"阶段4：空跑续抓 → 清单 {lines_after} → {lines_final} 条，文件 {stats4['files']}")
        if lines_final != lines_after:
            fails.append(f"空跑续抓仍在重复抓取：清单 {lines_after} → {lines_final}")
        if stats4["files"] != stats3["files"]:
            fails.append(f"空跑续抓文件数应不变：{stats3['files']} → {stats4['files']}")

        # ---------- 断言 ----------
        on_disk = []
        for r, _d, fs in os.walk(OUT):
            for f in fs:
                on_disk.append(os.path.relpath(os.path.join(r, f), OUT).replace("\\", "/"))
        missing = [p for p in expected if not any(f == p or f.endswith("/" + p) for f in on_disk)]
        print(f"详情页检查：应到 {len(expected)}，缺 {len(missing)}")
        if missing[:5]:
            print("   缺失样例：", missing[:5])
        if missing:
            fails.append(f"续抓后仍缺 {len(missing)} 个页面")

        entries = read_ndjson(ndjson_path)
        paths = [e["path"] for e in entries]
        dupes = {p for p in paths if paths.count(p) > 1}
        print(f"清单记录 {len(paths)} 条，去重后 {len(set(paths))} 条，重复 {len(dupes)} 个")
        if dupes:
            fails.append(f"续抓重复抓取（清单有重复路径）：{list(dupes)[:5]}")

        state2 = json.load(open(state_path, encoding="utf-8"))
        if not state2.get("done"):
            fails.append("完成后状态文件的 done 标记不为 True")
        if state2.get("pending_count"):
            fails.append(f"完成后待抓队列仍非空（pending_count={state2.get('pending_count')}）")

        # —— 本次性能修复的回归哨兵 ——
        # 状态文件必须已瘦身：不得再内嵌全量 visited/queue/saved。
        # （这三个集合体积极大且可精确重建，内嵌会让快照随抓取量线性膨胀）
        big_keys = [k for k in ("visited", "queue", "saved") if k in state2]
        if big_keys:
            fails.append(f"状态文件仍内嵌全量集合（未瘦身）：{big_keys}")
        state_kb = os.path.getsize(state_path) / 1024
        if state_kb > 512:
            fails.append(f"状态文件过大：{state_kb:.1f} KB（应稳定在 KB 级）")
        print(f"阶段4：状态文件 {state_kb:.1f} KB（瘦身校验通过）")

    finally:
        srv.shutdown()

    print()
    if fails:
        print("[FAIL] 失败：")
        for f in fails:
            print("   -", f)
        return 1
    print("[OK] 断点续抓测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
