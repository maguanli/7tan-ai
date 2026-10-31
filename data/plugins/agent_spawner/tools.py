# -*- coding: utf-8 -*-
"""子 Agent 派工插件 —— AI 指挥 AI（串行版 v1）

设计取舍（为什么是串行）：
    7tanAI 里有两条资源是【进程级独占】的：
      · 浏览器：browser_tools 里的 _source_view / _admin_view 是模块级单例，没有锁
      · 桌面：鼠标键盘只有一套
    两个 Worker 同时碰这两样，会互相把页面切走、把输入抢走。
    所以 v1 只允许同时跑一个 Worker：并发的前提不是 CPU 和 Token，而是"独占资源只有一条"。

    串行版另外回避了一个已知缺陷：src/utils/abort_signal.py 的 _signals 是模块级列表，
    is_aborted() 的语义是"任一信号 set 即判中止"。多 Worker 并发时，中止 A 会连坐 B。
    该缺陷在 P1 并发化之前必须修（按 session 隔离），届时本插件的 _RUN_LOCK 才可放开。

安全边界（无人值守时不能给的东西）：
    Worker 是被派出去干活的，此刻没有人在旁边看着。self_modify_* 那几个
    （改自己配置 / 重建自己 / 重启自己）在这种场合是不可逆操作：
    它能趁没人看着重写自身，证据随重启一起消失。
    因此默认剔除，需要时用 allow_self_modify=True 显式打开——这是"限制场合"，不是"减少能力"。

    其余 270+ 个工具全部原样下放，不做领域裁剪。
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.tools.registry import register_tool, get_all_tools

# ── 路径 ────────────────────────────────────────────────────
_PLUGIN_DIR = Path(__file__).parent                  # data/plugins/agent_spawner
_ROOT = _PLUGIN_DIR.parent.parent.parent            # 项目根
_RUN_DIR = _ROOT / "data" / "spawn_worker"
_RUN_LOG = _RUN_DIR / "runs.jsonl"
_FULL_DIR = _RUN_DIR / "reports"

# ── 串行闸门 ────────────────────────────────────────────────
_RUN_LOCK = threading.Lock()          # 保证同一时刻只有一个 Worker
_STATE = {"running": False, "worker_id": None, "started_at": None, "task_head": None}

# 不能下放给 Worker 的工具：会无限套娃，或没人看着时不该动
_SELF_TOOLS = {"spawn_worker", "spawn_status"}

# 自伤类：没人看着时能改写/重建/重启自身，证据随重启一起消失。
# 判据不能只看名字前缀 —— self_rebuild / self_update_prompt / sandbox_execute
# 的 category 都是 self_modify 但名字不是这个前缀，只看前缀会漏掉。
# 这里沿用 registry 已有的 pro_only 门控语义（category == "self_modify"）。
_SELF_MODIFY_CATEGORY = "self_modify"
_SELF_MODIFY_EXTRA = {
    "self_restart",       # 重启应用，现场证据没了
    "self_fix_sandbox",   # 自己给自己做手术
    "create_plugin",      # 动态新增工具，等于改自身能力面
}


class _WorkerAbort(threading.Event):
    """带原因码的中止信号（run_agent_loop 会读 .reason 填中止原因）。"""

    def __init__(self, reason: str = "timeout"):
        super().__init__()
        self.reason = reason


def _is_self_harm(name: str) -> bool:
    """判断某工具是否属于「无人值守时不该给」的自伤类。"""
    if not name:
        return True
    if name in _SELF_MODIFY_EXTRA:
        return True
    try:
        from src.tools.registry import TOOL_REGISTRY
        t = TOOL_REGISTRY.get(name)
        cat = getattr(t, "category", None)
        if cat == _SELF_MODIFY_CATEGORY:
            return True
        try:
            if t is not None and not hasattr(t, "name") and t.get("category") == _SELF_MODIFY_CATEGORY:
                return True
        except Exception:
            pass
    except Exception:
        pass
    return name.startswith("self_modify")


def _pick_tools(allow_self_modify: bool):
    """下放给 Worker 的工具集：全量减去自身与自伤类。"""
    all_tools = get_all_tools() or []
    picked, dropped = [], []
    for t in all_tools:
        name = ((t or {}).get("function") or {}).get("name") or ""
        if name in _SELF_TOOLS:
            dropped.append(name)
            continue
        if not allow_self_modify and _is_self_harm(name):
            dropped.append(name)
            continue
        picked.append(t)
    return picked, dropped


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(_ROOT)).replace("\\", "/")
    except Exception:
        return str(p)


def _append_log(record: dict) -> None:
    try:
        _RUN_DIR.mkdir(parents=True, exist_ok=True)
        with open(_RUN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"spawn_worker 写日志失败: {e}")


def _read_recent(n: int = 10) -> list:
    if not _RUN_LOG.exists():
        return []
    try:
        lines = _RUN_LOG.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        return [json.loads(x) for x in lines[-n:] if x.strip()]
    except Exception:
        return []


DEFAULT_WORKER_PROMPT = """你是一个被派工的子 Agent（Worker）。你不是在跟用户对话，是在替派工方完成一件具体的事。

工作方式：
1. 直接动手，能用工具验证的就去验证，不要靠猜测下结论。
2. 完成后给一份结论：做了什么、结果是什么、有哪些没做到。
3. 不要反问、不要请求确认、不要输出"如果要继续请告诉我"之类的话——派工方不在你这一侧等待。
4. 不确定的地方明确写"未核实"，不要编造。

你的输出会作为报告回传给派工方，请写得可核对：给出文件路径、命令输出、数字，而不是形容词。"""


@register_tool(
    name="spawn_worker",
    description=(
        "派一个子 Agent（Worker）去独立完成一件完整的子任务，拿回报告。"
        "主 Agent 拆活、派活、汇总；Worker 在自己的 session 里独立跑，不占用主对话上下文。"
        "适合：边界清楚、能独立做完、结论可核对的活（比如「把 X 目录里的文章按 Y 规范改一遍并验证」）。"
        "不适合：需要边做边跟用户确认的活，或者一句话就能答的事。"
        "注意：串行执行，同一时刻只能跑一个 Worker，忙时会直接返回提示。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "派给 Worker 的任务书。要写清：目标、输入在哪、验收标准、不能做什么。写得越具体，Worker 越不容易跑偏。",
            },
            "max_iterations": {
                "type": "integer",
                "description": "最大迭代轮数，默认 200，硬上限 500。跑偏的 Worker 会烧轮次，不要随手调到 1000。",
                "default": 200,
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "墙钟超时秒数，默认 1800（30 分钟），上限 7200。超时会中止 Worker 并返回已产生的部分结果。",
                "default": 1800,
            },
            "allow_self_modify": {
                "type": "boolean",
                "description": "是否把 self_modify_*（改自身配置/重建/重启）下放给 Worker。默认 False——无人值守时这些是不可逆操作。",
                "default": False,
            },
            "system_prompt": {
                "type": "string",
                "description": "Worker 的角色提示词，留空用内置的通用派工提示。",
                "default": "",
            },
        },
        "required": ["task"],
    },
    category="agent",
)
def spawn_worker(task: str, max_iterations: int = 200, timeout_seconds: int = 1800,
                 allow_self_modify: bool = False, system_prompt: str = "") -> str:
    """串行派一个 Worker 干活，返回结构化报告。"""
    task = (task or "").strip()
    if not task:
        return "❌ spawn_worker: task 不能为空"

    # 串行闸门：忙则立即返回，不阻塞主对话
    if not _RUN_LOCK.acquire(blocking=False):
        cur = _STATE.get("worker_id") or "?"
        return (
            f"⏳ 已有一个 Worker 在跑（{cur}，任务：{(_STATE.get('task_head') or '')[:60]}）。\n"
            f"本插件是串行版：同时只允许一个 Worker，避免两个 Worker 抢浏览器和桌面。\n"
            f"等它结束再派，或用 spawn_status 查看进度。"
        )

    worker_id = f"w-{datetime.now().strftime('%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
    max_iterations = max(10, min(int(max_iterations or 200), 500))
    timeout_seconds = max(60, min(int(timeout_seconds or 1800), 7200))

    _STATE.update({"running": True, "worker_id": worker_id,
                   "started_at": time.time(), "task_head": task[:200]})

    abort_event = _WorkerAbort(reason="timeout")
    timer = threading.Timer(timeout_seconds, lambda: abort_event.set())
    timer.daemon = True
    timer.start()

    tools, dropped = _pick_tools(allow_self_modify)
    started = time.time()
    result = {}
    error = None
    try:
        from src.agent.agent_loop import run_agent_loop

        result = run_agent_loop(
            task=task,
            tools=tools,                      # 显式传：不传会退回 276 个全量
            session_id=worker_id,             # 独立会话，不污染主对话
            system_prompt=(system_prompt or DEFAULT_WORKER_PROMPT),
            max_iterations=max_iterations,
            abort_event=abort_event,          # 独立信号，互不连坐
        ) or {}
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        logger.error(f"spawn_worker {worker_id} 异常: {error}")
    finally:
        timer.cancel()
        elapsed = round(time.time() - started, 1)
        _STATE.update({"running": False, "worker_id": None, "started_at": None, "task_head": None})
        _RUN_LOCK.release()

    success = bool(result.get("success"))
    text = str(result.get("result") or "")

    # 完整报告落盘，只把摘要回灌主上下文（省 token）
    full_path = None
    try:
        _FULL_DIR.mkdir(parents=True, exist_ok=True)
        fp = _FULL_DIR / f"{worker_id}.md"
        fp.write_text(
            f"# Worker {worker_id}\n\n## 任务\n{task}\n\n## 结果\n{text}\n\n"
            f"## 元信息\n- success: {success}\n- iterations: {result.get('iterations')}\n"
            f"- cost: {result.get('cost')}\n- tokens: {result.get('total_tokens')}\n"
            f"- elapsed: {elapsed}s\n- aborted: {abort_event.is_set()}\n- error: {error}\n",
            encoding="utf-8",
        )
        full_path = fp
    except Exception as e:
        logger.warning(f"spawn_worker 写完整报告失败: {e}")

    record = {
        "worker_id": worker_id,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "success": success,
        "iterations": result.get("iterations"),
        "cost": result.get("cost"),
        "total_tokens": result.get("total_tokens"),
        "elapsed_s": elapsed,
        "aborted": abort_event.is_set(),
        "error": error,
        "tools": len(tools),
        "dropped": dropped,
        "task": task[:500],
        "report": _rel(full_path) if full_path else None,
    }
    _append_log(record)

    # ── 回传给主 Agent 的摘要 ──
    head = [
        f"【Worker {worker_id}】{'✅ 完成' if success else '❌ 未完成'}",
        f"轮数 {result.get('iterations')}  耗时 {elapsed}s  成本 ¥{result.get('cost')}  "
        f"工具 {len(tools)} 个",
    ]
    if abort_event.is_set():
        head.append("⚠️ 已超时中止，下面是中止前已有的结果")
    if error:
        head.append(f"⚠️ 异常：{error}")
    if dropped:
        head.append(f"（未下放：{', '.join(dropped)}）")
    if full_path:
        head.append(f"完整报告：{_rel(full_path)}")

    limit = 4000
    body = text if len(text) <= limit else text[:limit] + f"\n…（截断，共 {len(text)} 字符，全文见报告文件）"
    return "\n".join(head) + "\n\n" + (body or "（Worker 没有产出文本结论）")


@register_tool(
    name="spawn_status",
    description="查看子 Agent 派工插件的状态：当前是否有 Worker 在跑、跑的是哪个任务，以及最近几次派工的记录（成败/轮数/耗时/成本）。",
    parameters={
        "type": "object",
        "properties": {
            "recent": {"type": "integer", "description": "回显最近几条历史记录，默认 5", "default": 5},
        },
        "required": [],
    },
    category="agent",
)
def spawn_status(recent: int = 5) -> str:
    """查看派工状态与历史。"""
    out = []
    if _STATE.get("running"):
        el = round(time.time() - (_STATE.get("started_at") or time.time()), 1)
        out.append(f"🏃 正在跑：{_STATE.get('worker_id')}  已 {el}s")
        out.append(f"   任务：{(_STATE.get('task_head') or '')[:120]}")
    else:
        out.append("💤 空闲，没有 Worker 在跑")

    rows = _read_recent(max(1, min(int(recent or 5), 50)))
    if rows:
        out.append("\n最近派工：")
        for r in reversed(rows):
            flag = "✅" if r.get("success") else "❌"
            extra = " 超时中止" if r.get("aborted") else ""
            out.append(
                f"  {flag} {r.get('worker_id')}  {r.get('ts')}  "
                f"{r.get('iterations')}轮 {r.get('elapsed_s')}s ¥{r.get('cost')}{extra}"
            )
            out.append(f"      {str(r.get('task') or '')[:80]}")
    else:
        out.append("\n还没有派工记录。")
    out.append("\n说明：串行版，同时只允许一个 Worker（浏览器/桌面是进程级独占资源）。")
    return "\n".join(out)
