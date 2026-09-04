"""
意识模型 API —— 7Tan 仿生器官框架实时状态读取
GET /api/mind/status — 一次性快照：心跳 / 器官模块 / 长期记忆 / 自我模型 / 事件总线 / 假设库

设计约束（遵守架构红线）：
  1. 只读——绝不调用 organ_tick_all / emit_event / 任何写入口，纯观测；
  2. 线程安全——用内核 _TICK_LOCK 保护快照读取，避免与后台心跳 tick 交叉读到半成品；
  3. 惰性——器官框架未初始化时返回空数据，不抛异常、不阻塞页面；
  4. 只溯源，不编造——所有字段直读内核结构化状态，不做任何文本杜撰。
"""
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
