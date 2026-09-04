"""
意识模型 API —— 7Tan 仿生器官框架实时状态读取
GET /api/mind/status — 一次性快照：心跳 / 器官模块 / 长期记忆 / 自我模型 / 事件总线 / 假设库

设计约束（遵守架构红线）：
  1. 只读——绝不调用 organ_tick_all / emit_event / 任何写入口，纯观测；
  2. 线程安全——用内核 _TICK_LOCK 保护快照读取，避免与后台心跳 tick 交叉读到半成品；
  3. 惰性——器官框架未初始化时返回空数据，不抛异常、不阻塞页面；
  4. 只溯源，不编造——所有字段直读内核结构化状态，不做任何文本杜撰。
"""
import time
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/mind", tags=["mind"])


def _snapshot() -> dict:
    """在 _TICK_LOCK 内读取器官框架全部实时状态，返回纯 JSON 可序列化快照。"""
    try:
        from ...agent import bionic_organs as bo
    except Exception:
        return {"ok": False, "error": "器官框架未挂载"}

    lock = getattr(bo, "_TICK_LOCK", None)
    acquired = False
    if lock is not None:
        try:
            acquired = lock.acquire(timeout=2.0)
        except Exception:
            acquired = False

    try:
        # —— 心跳 ——
        hb_thread = getattr(bo, "_heartbeat_thread", None)
        heartbeat = {
            "tick_counter": int(getattr(bo, "_organ_tick_counter", 0) or 0),
            "subjective_clock": _f(bo, "subjective_time", "subjective_clock"),
            "time_dilation": _f(bo, "subjective_time", "time_dilation"),
            "alive": bool(hb_thread is not None and hb_thread.is_alive()),
            "enabled": bool(getattr(bo, "_HEARTBEAT_ENABLED", False)),
            "interval_sec": float(getattr(bo, "_HEARTBEAT_INTERVAL", 120.0) or 120.0),
        }

        # —— 器官模块（14 个）——
        organs = []
        registry = getattr(bo, "organ_registry", {}) or {}
        for code in sorted(registry.keys()):
            o = registry.get(code)
            if o is None:
                continue
            organs.append({
                "code": code,
                "name": getattr(o, "organ_name", ""),
                "module": getattr(o, "module_name", ""),
                "bio": getattr(o, "bio_analogy", ""),
                "enabled": bool(getattr(o, "enabled", False)),
                "config": _safe_dict(getattr(o, "config", {})),
            })

        # —— 长期记忆（ORG-A memory_library，最近 50 条倒序）——
        lib = getattr(bo, "memory_library", []) or []
        memory = []
        for m in lib[-50:][::-1]:
            if not isinstance(m, dict):
                continue
            memory.append({
                "thought": _trunc(str(m.get("thought", "")), 120),
                "focus": _trunc(str(m.get("focus", "") or ""), 40),
                "valence": m.get("valence"),
                "origin": m.get("origin", "internal"),
                "subjective_time": m.get("subjective_time"),
                "weight_eff": _fnum(m.get("weight_eff")),
                "goal_tag": _trunc(str(m.get("goal_tag", "") or ""), 40),
                "pe": _fnum(m.get("pe")),
                "success": m.get("success"),
            })

        # —— 自我模型（ORG-SELFMODEL）——
        self_model = _safe_dict(getattr(bo, "self_model_data", {}))

        # —— 工作记忆（ORG-E）——
        wm = _safe_dict(getattr(bo, "working_memory", {}))
        active_goals = list(wm.get("active_goals", []) or [])[-10:]
        working_memory = {
            "active_goals": active_goals,
            "context_stack_len": len(wm.get("context_stack", []) or []),
        }

        # —— 事件总线 ——
        try:
            bus = bo.bus_stats()
        except Exception:
            bus = {}
        bus = _safe_dict(bus)
        replay_total = sum(int(v or 0) for v in (bus.get("replay_buffer") or {}).values())

        # —— 假设库 / 来源统计（我-非我边界）/ 元认知 ——
        hypotheses = []
        for h in (getattr(bo, "hypothesis_registry", []) or [])[-50:][::-1]:
            if isinstance(h, dict):
                hypotheses.append(_safe_dict(h))
        origin_stats = _safe_dict(getattr(bo, "origin_stats", {}))
        meta_cognition = _safe_dict(getattr(bo, "meta_cognition_stats", {}))
        # 预测误差历史只保留统计摘要，不吐全量数组
        pe_samples = list(meta_cognition.get("pe_samples", []) or [])
        meta_summary = {
            "hypo_accepted": meta_cognition.get("hypo_accepted", 0),
            "hypo_rejected": meta_cognition.get("hypo_rejected", 0),
            "pe_sample_count": len(pe_samples),
            "pe_mean_recent": round(sum(float(x) for x in pe_samples[-20:]) / max(1, len(pe_samples[-20:])), 4) if pe_samples else None,
        }

        # —— 最近事件（_event_log 最后 50 条倒序）——
        recent_events = []
        for ev in (getattr(bo, "_event_log", []) or [])[-50:][::-1]:
            if isinstance(ev, dict):
                recent_events.append({
                    "ts": ev.get("ts"),
                    "tick": ev.get("tick"),
                    "subj": ev.get("subj"),
                    "type": ev.get("type"),
                    "origin": ev.get("origin"),
                    "src": ev.get("src"),
                })

        return {
            "ok": True,
            "heartbeat": heartbeat,
            "organs": organs,
            "organ_count": len(organs),
            "enabled_count": sum(1 for o in organs if o["enabled"]),
            "memory": memory,
            "memory_total": len(lib),
            "self_model": self_model,
            "working_memory": working_memory,
            "bus": {
                "queue_len": bus.get("queue_len", 0),
                "log_len": bus.get("log_len", 0),
                "replay_buffer_total": replay_total,
                "subscription_count": len(bus.get("subscriptions") or {}),
            },
            "hypotheses": hypotheses,
            "hypothesis_count": len(getattr(bo, "hypothesis_registry", []) or []),
            "origin_stats": origin_stats,
            "meta_cognition": meta_summary,
            "recent_events": recent_events,
            "learning": _learning_snapshot(),
        }
    finally:
        if lock is not None and acquired:
            try:
                lock.release()
            except Exception:
                pass


def _safe_dict(v) -> dict:
    return v if isinstance(v, dict) else {}


def _f(bo, var, key, default=0.0):
    try:
        d = getattr(bo, var, {}) or {}
        if isinstance(d, dict):
            return d.get(key, default)
    except Exception:
        pass
    return default


def _fnum(v):
    try:
        return round(float(v), 4)
    except Exception:
        return None


def _trunc(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n] + "…"


@router.get("/status")
async def mind_status():
    """意识模型实时快照（只读）。"""
    return _snapshot()


# ═══════════════ 自我学习模块（L1 模块F + L2 模块D + M1 知识获取）═══════════════
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # src/web/routes -> 项目根
_HYPO_LOG = _PROJECT_ROOT / "data" / "tan_hypothesis.log"
_EVOLUTION_LOG = _PROJECT_ROOT / "data" / "tan_evolution.log"


def _tail_file(path: Path, n: int = 15) -> list:
    """读取日志文件末尾 n 行（只读，容错）。"""
    try:
        if not path.exists():
            return []
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:]
    except Exception:
        return []


def _get_tan_model():
    """只读获取 TanModel 单例；未初始化返回 None（不强行创建，避免副作用）。"""
    try:
        import src.agent.world_model as wm_mod
        return getattr(wm_mod, "_TAN_MODEL_SINGLETON", None)
    except Exception:
        return None


def _learning_snapshot() -> dict:
    """自我学习实时快照：L1 记忆学习 + L2 进化 + M1 知识获取（全部只读，不注入不 tick）。"""
    data = {
        "l1": {"ready": False, "hypotheses": {"stats": {}, "recent": []},
               "dialog": [], "dialog_total": 0,
               "knowledge": [], "knowledge_total": 0, "recent_log": []},
        "l2": {"ready": False, "status": {}, "constants": {}, "recent_log": []},
        "m1": {"ready": False, "mounted": False, "package_pending": 0,
               "package_processed": 0, "web_queue": 0, "rate_limit": 0},
    }
    wm = _get_tan_model()

    # ── L1 模块F 记忆级学习 ──
    sl = getattr(wm, "selflearn", None) if wm else None
    if sl is not None:
        data["l1"]["ready"] = True
        reg = getattr(sl, "hypothesis_registry", []) or []
        stat = {"total": len(reg), "pending": 0, "verified": 0,
                "rejected": 0, "suspended": 0}
        recent = []
        for h in reg[-20:][::-1]:
            d = h.to_dict() if hasattr(h, "to_dict") else h
            if not isinstance(d, dict):
                continue
            st = str(d.get("status", "pending"))
            stat[st] = stat.get(st, 0) + 1
            recent.append({
                "id": d.get("hypothesis_id", ""),
                "content": _trunc(str(d.get("content", "")), 90),
                "status": st,
                "confidence": d.get("final_confidence"),
                "raw": d.get("confidence_raw"),
                "test_count": d.get("test_count"),
                "success_count": d.get("success_count"),
                "fail_count": d.get("fail_count"),
            })
        data["l1"]["hypotheses"] = {"stats": stat, "recent": recent}

        mem = getattr(wm, "memory", None)
        traces = getattr(mem, "traces", []) or []
        dialogs = [t for t in traces if isinstance(t, dict) and t.get("scene") == "dialog"]
        data["l1"]["dialog_total"] = len(dialogs)
        data["l1"]["dialog"] = [{
            "action": _trunc(str(d.get("action", "")), 30),
            "user_text": _trunc(str(d.get("user_text", "")), 60),
            "reply": _trunc(str(d.get("reply", "")), 80),
            "intent": _trunc(str(d.get("intent", "")), 20),
            "ts": d.get("ts"),
        } for d in dialogs[-15:][::-1]]

        knowledge = getattr(mem, "knowledge", []) or []
        data["l1"]["knowledge_total"] = len(knowledge)
        data["l1"]["knowledge"] = [{
            "key": _trunc(str(k.get("key", "")), 40),
            "content": _trunc(str(k.get("content", "")), 100),
            "source": k.get("source", ""),
            "ts": k.get("ts"),
        } for k in knowledge[-15:][::-1] if isinstance(k, dict)]
        data["l1"]["recent_log"] = _tail_file(_HYPO_LOG, 15)

    # ── L2 模块D 进化 ──
    ev = getattr(wm, "evolve", None) if wm else None
    if ev is not None:
        data["l2"]["ready"] = True
        try:
            data["l2"]["status"] = ev.status()
        except Exception:
            pass
        try:
            data["l2"]["constants"] = ev._current_constants()
        except Exception:
            pass
        data["l2"]["recent_log"] = _tail_file(_EVOLUTION_LOG, 15)

    # ── M1 知识获取 ──
    try:
        from src.agent.upper_m1_knowledge import get_m1
        m1 = get_m1()
        data["m1"]["ready"] = True
        data["m1"]["mounted"] = bool(getattr(m1, "_mounted", False))
        pkg = getattr(m1, "pkg_queue", None)
        data["m1"]["package_pending"] = len(getattr(pkg, "pending", []) or [])
        data["m1"]["package_processed"] = len(getattr(pkg, "processed_ids", set()) or set())
        data["m1"]["web_queue"] = len(getattr(m1, "_deep_queue", []) or [])
        data["m1"]["rate_limit"] = getattr(getattr(m1, "limiter", None), "rate", 0)
    except Exception:
        pass

    return data


@router.post("/knowledge-package")
async def mind_import_knowledge(payload: dict):
    """下载知识包：支持网页 URL 抓取（web_fetch）或直接文本条目导入（knowledge_package）。

    只投递外部素材，不改任何器官算法；统一走 M1 限速器与游标去重（遵 C5）。
    """
    payload = payload or {}
    url = payload.get("url")
    entries = payload.get("entries")
    try:
        from src.agent.upper_m1_knowledge import get_m1
        m1 = get_m1()
        if url:
            u = str(url).strip()
            if not (u.startswith("http://") or u.startswith("https://")):
                return {"ok": False, "error": "URL 必须以 http:// 或 https:// 开头"}
            n = m1.learn_from_web(u, trigger="manual")
            return {"ok": True, "action": "web_fetch", "queued": n, "url": u}
        if isinstance(entries, list) and entries:
            items = []
            for i, e in enumerate(entries):
                if isinstance(e, dict):
                    content = str(e.get("content", "") or "").strip()
                    if not content:
                        continue
                    iid = str(e.get("item_id", "") or "") or f"manual-{int(time.time())}-{i}"
                    items.append({"item_id": iid, "content": content})
            if not items:
                return {"ok": False, "error": "没有可导入的有效知识条目"}
            n = m1.import_knowledge_package(items)
            return {"ok": True, "action": "knowledge_package", "imported": n}
        return {"ok": False, "error": "缺少 url 或 entries 参数"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
