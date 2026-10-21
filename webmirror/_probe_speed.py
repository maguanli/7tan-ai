# -*- coding: utf-8 -*-
"""对比：往 youbian.293.net 子树 / youbian.293.net2 新目录 / 对照新目录 写文件的吞吐。"""
import os, time, threading, subprocess, json, sys

BASE = r"D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb"
OLD  = os.path.join(BASE, "youbian.293.net")
NEW  = os.path.join(BASE, "youbian.293.net2")
CTRL = os.path.join(BASE, "__probe_ctrl")

DUR = 20.0        # 每个目标最多测 20 秒
THREADS = 4

def attrs(p):
    d = {"exists": os.path.isdir(p)}
    if d["exists"]:
        st = os.stat(p)
        a = getattr(st, "st_file_attributes", 0)
        d["attrib_hex"] = hex(a)
        d["REPARSE_POINT"] = bool(a & 0x400)
        d["COMPRESSED"] = bool(a & 0x800)
        d["ENCRYPTED"] = bool(a & 0x4000)
        d["reparse_tag"] = getattr(st, "st_reparse_tag", None)
    return d

def bench(target, label):
    sub = os.path.join(target, "__probe__")
    try:
        os.makedirs(sub, exist_ok=True)
    except Exception as e:
        return {"label": label, "error": f"makedirs failed: {e}"}
    data = b"x" * 2048
    t0 = time.time()
    deadline = t0 + DUR
    cnt = [0]
    errs = []
    lock = threading.Lock()

    def worker(tid):
        i = 0
        while True:
            if time.time() > deadline:
                break
            p = os.path.join(sub, f"w{tid}_{i}.part")
            q = os.path.join(sub, f"w{tid}_{i}.html")
            try:
                with open(p, "wb") as f:
                    f.write(data)
                os.replace(p, q)
                with lock:
                    cnt[0] += 1
            except Exception as e:
                with lock:
                    if len(errs) < 3:
                        errs.append(repr(e))
            i += 1

    ths = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    dt = time.time() - t0
    return {"label": label, "files": cnt[0], "sec": round(dt, 2),
            "per_sec": round(cnt[0] / dt, 2) if dt else 0, "errs": errs}

out = {}
out["OLD_atts"] = attrs(OLD)
out["NEW_atts_before"] = attrs(NEW)
os.makedirs(NEW, exist_ok=True)
os.makedirs(CTRL, exist_ok=True)
out["NEW_atts_after"] = attrs(NEW)
out["CTRL_atts"] = attrs(CTRL)

# 看老目录是不是 junction / 有特殊属性
try:
    r = subprocess.run(["fsutil", "reparsepoint", "query", OLD],
                       capture_output=True, text=True, timeout=10)
    out["fsutil_old"] = (r.stdout or r.stderr)[:400]
except Exception as e:
    out["fsutil_old"] = repr(e)

out["bench_old"]  = bench(OLD,  "youbian.293.net 子树")
out["bench_new"]  = bench(NEW,  "youbian.293.net2 新目录")
out["bench_ctrl"] = bench(CTRL, "对照新目录")

# 清理探针
import shutil
for d in (OLD, NEW, CTRL):
    p = os.path.join(d, "__probe__")
    try:
        shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass
try:
    os.rmdir(CTRL)
except Exception:
    pass

print(json.dumps(out, ensure_ascii=False, indent=2))
