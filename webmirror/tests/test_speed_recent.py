"""面板「最近 60 秒实时速度」—— 防止被累计平均值误导的回归哨兵。

背景（真实困惑，勿回退）
-----------------------
面板原来的 speed = done / elapsed，是**自任务开始至今的累计平均**。
长任务跑久了必然被历史低谷期稀释：实测 youbian 任务已跑 25 小时，
性能修复后实时吞吐已达 5.4/s，面板却仍显示 3.3/s —— 看起来像没提速。
本测试锁死：实时速度必须只看滑动窗口，与历史累计解耦。
"""
import asyncio
import time

from app.crawler import CrawlConfig, Mirror


def _mk(tmp_path, **kw) -> Mirror:
    cfg = CrawlConfig(start_url="http://x.test/", out_root=str(tmp_path), **kw)
    m = Mirror(cfg)
    m.queue = asyncio.Queue()
    return m


def _ticks(m: Mirror, n: int, span: float) -> None:
    """在 [now-span, now] 内均匀打 n 个点（模拟 n 个完成的页面/资源）。"""
    now = time.time()
    for i in range(n):
        m._recent.append(now - span + (span * i / max(1, n)))


def test_recent_speed_is_not_diluted_by_history(tmp_path):
    """跑了一小时、最近 60 秒在提速：平均值骗人，实时值必须说真话。"""
    m = _mk(tmp_path)
    now = time.time()
    m.stats["started_at"] = now - 3600          # 已跑 1 小时
    m.stats["pages_ok"] = 3600                  # 累计完成 3600 → 平均 1.0/s
    _ticks(m, 600, 59.0)                        # 最近 60 秒完成 600 → 实时 10/s

    st = m.snapshot()
    assert st["speed"] == 1.0, f"累计平均应被历史稀释为 1.0，实得 {st['speed']}"
    assert 9.0 <= st["speed_recent"] <= 11.0, \
        f"实时速度应约 10/s，实得 {st['speed_recent']}"
    assert st["speed_window"] == 60


def test_window_prunes_old_ticks(tmp_path):
    """窗口外的打点必须被淘汰，内存不随任务时长无限增长。"""
    m = _mk(tmp_path)
    now = time.time()
    m.stats["started_at"] = now - 1000
    for i in range(500):                        # 全部落在 600 秒之前
        m._recent.append(now - 900 + i * 0.5)
    assert len(m._recent) == 500

    st = m.snapshot()
    assert len(m._recent) == 0, "窗口外打点未被淘汰"
    assert st["speed_recent"] == 0.0


def test_warmup_divides_by_real_elapsed(tmp_path):
    """任务刚跑几秒：分母应是实际时长，而不是完整的 60 秒。"""
    m = _mk(tmp_path)
    now = time.time()
    m.stats["started_at"] = now - 5             # 才跑了 5 秒
    _ticks(m, 50, 4.5)                          # 完成 50 个
    st = m.snapshot()
    # 若错误地除以 60，会得到 0.8/s（严重低估）；正确应约 10/s
    assert st["speed_recent"] >= 8.0, \
        f"预热期被 60 秒分母低估：{st['speed_recent']}"


def test_finished_task_uses_finished_at(tmp_path):
    """任务结束后冻结在结束时刻，不再随时间流逝而衰减。"""
    m = _mk(tmp_path)
    now = time.time()
    m.stats["started_at"] = now - 100
    m.stats["finished_at"] = now - 40           # 40 秒前结束
    _ticks(m, 40, 39.0)
    st1 = m.snapshot()
    time.sleep(0.2)
    st2 = m.snapshot()
    assert st1["speed_recent"] == st2["speed_recent"], "已结束任务的速度不应继续变化"
    assert 0.5 <= st1["speed_recent"] <= 1.5, f"实得 {st1['speed_recent']}"


def test_empty_window_is_zero(tmp_path):
    """还没抓任何东西时显示 0，不能出现除零/NaN。"""
    m = _mk(tmp_path)
    m.stats["started_at"] = time.time()
    st = m.snapshot()
    assert st["speed_recent"] == 0.0
    assert st["speed_recent"] == st["speed_recent"]      # 非 NaN


def test_write_appends_tick(tmp_path):
    """_write（唯一落盘出口）必须打点，口径与 pages_ok + assets_ok 一致。"""
    m = _mk(tmp_path)
    m.stats["started_at"] = time.time()
    assert len(m._recent) == 0
    asyncio.run(m._write("x.test/a.html", b"<html></html>",
                         "http://x.test/a.html", "text/html", 200))
    asyncio.run(m._write("x.test/b.css", b"body{}",
                         "http://x.test/b.css", "text/css", 200))
    assert len(m._recent) == 2, "落盘未打点"
    assert m.stats["files"] == 2


def test_recent_speed_matches_point_count_over_window(tmp_path):
    """窗口内打点数 / 窗口跨度 的数值关系必须精确成立（非近似）。"""
    m = _mk(tmp_path)
    now = time.time()
    m.stats["started_at"] = now - 3600          # 已过预热期，分母为满窗口 60
    _ticks(m, 300, 59.5)
    st = m.snapshot()
    assert st["speed_recent"] == round(300 / 60.0, 1), \
        f"应为 5.0，实得 {st['speed_recent']}"
