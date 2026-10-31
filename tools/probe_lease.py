# -*- coding: utf-8 -*-
"""验证资源租约：冲突能不能真被排队解决。

对照关系（同一批冲突，加租约前后）：
    L1-4 同一文件读-改-写 8×40   冲突时丢 97% 更新
    L1-5 同一仓库并发 git 写      冲突时 17/24 撞 index.lock
    L3-1 浏览器 _active_ctx 被切  冲突时操作错误窗口且不报错
"""
import sys
import threading
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils import resource_lease as L

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ✅ " if ok else "  ❌ ") + name + (("  " + str(detail)) if detail else ""))


def section(t):
    print("\n" + "=" * 70)
    print(t)
    print("=" * 70)


# ── 1. 独占语义 ────────────────────────────────────────────
section("1  两个 Worker 抢同一资源：后来的必须等")
got = []


def grab(owner, timeout):
    t0 = time.time()
    try:
        l = L.acquire("browser", owner, timeout=timeout, sticky=True)
        got.append((owner, "acquired", round(time.time() - t0, 2)))
        time.sleep(0.5)
        L.release(l)
    except L.LeaseTimeout:
        got.append((owner, "timeout", round(time.time() - t0, 2)))


t1 = threading.Thread(target=grab, args=("w-A", 5))
t2 = threading.Thread(target=grab, args=("w-B", 0.3))
t1.start(); time.sleep(0.15); t2.start()
t1.join(10); t2.join(10)

a = [g for g in got if g[0] == "w-A"]
b = [g for g in got if g[0] == "w-B"]
check("先到的拿到资源", a and a[0][1] == "acquired", a)
check("后到的等待超时被拒（fail-closed）", b and b[0][1] == "timeout", b)
check("所有租约已释放", not L.status(), str(L.status()))


# ── 2. 重入不自杀 ─────────────────────────────────────────
section("2  同一持有人重复申请：重入，不把自己锁死")


def reenter():
    try:
        l1 = L.acquire("browser", "w-C", timeout=1, sticky=True)
        l2 = L.acquire("browser", "w-C", timeout=1, sticky=True)
        d = l2.depth
        L.release(l2)
        still = L.holder_of("browser")
        L.release(l1)
        after = L.holder_of("browser")
        return d, still, after
    except L.LeaseTimeout as e:
        return None, f"timeout:{e}", None


d, still, after = reenter()
check("同一持有人可重入", d == 2, f"depth={d}")
check("释放一层后仍持有", still == "w-C", f"holder={still}")
check("释放到底才让出", after is None, f"holder={after}")


# ── 3. 粘性租约跨调用保持（浏览器 _active_ctx 的场景）────────
section("3  粘性租约：A 持有时 B 碰不到，A 的上下文不会被切走")
ctx = {"value": "none"}
box = {}


def worker_a():
    l = L.acquire("browser", "w-A", timeout=3, sticky=True)
    try:
        ctx["value"] = "source"          # 相当于 use_source_browser()
        time.sleep(0.3)
        for _ in range(3):
            ctx["value"] = ctx["value"]  # 相当于后续 browse_page 读上下文
            time.sleep(0.1)
        box["a_saw"] = ctx["value"]
    finally:
        L.release(l)


def worker_b():
    time.sleep(0.05)
    try:
        l = L.acquire("browser", "w-B", timeout=0.5, sticky=True)
        ctx["value"] = "admin"           # 相当于 use_admin_browser()
        L.release(l)
        box["b"] = "切走了"
    except L.LeaseTimeout:
        box["b"] = "被拒（正确）"


ta = threading.Thread(target=worker_a)
tb = threading.Thread(target=worker_b)
ta.start(); tb.start(); ta.join(10); tb.join(10)

check("A 的上下文全程未被切走", box.get("a_saw") == "source", f"A 末尾看到={box.get('a_saw')}")
check("B 被拒而不是静默改状态", box.get("b") == "被拒（正确）", box.get("b"))


# ── 4. 文件路径租约：真实解决丢更新 ─────────────────────────
section("4  同一文件并发写：靠租约把丢更新降到 0")
tmp = ROOT / "data" / "_lease_counter.txt"
tmp.parent.mkdir(parents=True, exist_ok=True)
tmp.write_text("0", encoding="utf-8")

ROUNDS, THREADS = 40, 8
key = f"file:{str(tmp).lower()}"


def writer(wid):
    for _ in range(ROUNDS):
        with L.guard(key, f"w-{wid}", timeout=30):
            n = int(tmp.read_text(encoding="utf-8") or 0)
            time.sleep(0.0005)                    # 放大竞态窗口（同 L1-4）
            tmp.write_text(str(n + 1), encoding="utf-8")


ts = [threading.Thread(target=writer, args=(i,)) for i in range(THREADS)]
for t in ts:
    t.start()
for t in ts:
    t.join(120)

got_n = int(tmp.read_text(encoding="utf-8") or 0)
expect = ROUNDS * THREADS
check("加租约后无丢更新", got_n == expect, f"{got_n}/{expect}")
tmp.unlink(missing_ok=True)


# ── 5. 不同文件可并行（租约不能把不该串的也串起来）──────────
section("5  不同路径 / 不同资源不互相阻塞")
files = [ROOT / "data" / f"_lease_p{i}.txt" for i in range(3)]
for f in files:
    f.write_text("", encoding="utf-8")

t0 = time.time()
held = threading.Event()


def hold_path(f):
    with L.guard(f"file:{str(f).lower()}", f"w-{f.name}", timeout=5):
        held.wait(2)


ts = [threading.Thread(target=hold_path, args=(f,)) for f in files]
for t in ts:
    t.start()
time.sleep(0.4)
n_held = len(L.status())
check("3 个不同文件可同时持有（没有被过度串行）", n_held == 3, f"同时持有={n_held}")
held.set()
for t in ts:
    t.join(10)
for f in files:
    f.unlink(missing_ok=True)
check("并发耗时接近并行（非串行 3 倍）", time.time() - t0 < 2.5, f"{time.time()-t0:.2f}s")


# ── 6. 崩溃兜底：release_all ──────────────────────────────
section("6  Worker 异常退出：release_all 兜底，不留死锁")
l1 = L.acquire("browser", "w-X", sticky=True)
l2 = L.acquire("desktop", "w-X", sticky=True)
l3 = L.acquire("camera", "w-Y", sticky=True)      # 别人的资源，不该被清
freed = L.release_all("w-X")
check("清掉了 w-X 的两个资源", sorted(freed) == ["browser", "desktop"], freed)
check("没误清 w-Y 的 camera", L.holder_of("camera") == "w-Y", L.holder_of("camera"))
L.release_all("w-Y")
check("全部释放后无残留", not L.status(), str(L.status()))


# ── 7. 超时信息可读 ──────────────────────────────────────
section("7  等不到时的报错要说清是谁占着")
L.acquire("browser", "w-Z", timeout=1, sticky=True)
msg = ""
try:
    L.acquire("browser", "w-Q", timeout=0.2)
except L.LeaseTimeout as e:
    msg = str(e)
L.release_all("w-Z")
check("报错含资源名与持有人", "browser" in msg and "w-Z" in msg, msg)


section(f"汇总：{len(PASS)} 通过 / {len(FAIL)} 未通过")
if FAIL:
    print("未通过：" + "，".join(FAIL))
sys.exit(0 if not FAIL else 1)
