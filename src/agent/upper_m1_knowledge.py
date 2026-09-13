# -*- coding: utf-8 -*-
"""
阶段1｜上层模块 M1：双知识获取体系（互联网自学 + 预制知识包）

来源：7Tan可执行架构文档_修订终版 V1.2（阶段1）。
定位：上层只读模块。只经内核挂钩点（register_post_tick_hook / register_external_source /
      emit_event）接入，绝不修改任何器官内部算法（遵 C4）。
外部知识统一走 tool_result 事件，source 字段区分：web_fetch / knowledge_package（遵 C5）。

途径1 互联网自主学习：
  触发条件（内生动机 / 任务驱动 / 空闲定时）→ 网络抓取 → 超长文本分片
  → 封装 tool_result(source="web_fetch") 送入事件总线 → 走完整 tick 链路（效价/focus/巩固/遗忘）
途径2 预制知识包导入：
  知识包每条封装 tool_result(source="knowledge_package") → 复用同一限速器 rate≤3
  → 持久化游标 item_id 续读 + 记忆去重（防重启重复灌入）→ 走标准心智链路

边界声明（C3）：本模块只投递外部素材，不生成内部心智内容；不调用任何 LLM。
本模块自包含（仅依赖标准库 + loguru + 内核只读接口）。
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional

from loguru import logger

try:  # 内核只读接口（本模块唯一允许接触内核的方式）
    from src.agent.bionic_organs import (
        emit_event,
        register_post_tick_hook,
        register_external_source,
        memory_library,
        save_organ_state,
        subjective_time,
    )
except Exception:  # pragma: no cover
    emit_event = register_post_tick_hook = register_external_source = None  # type: ignore
    save_organ_state = None
    memory_library = []
    subjective_time = {"subjective_clock": 0.0}
    _org_tick_fn = None

# ═══════════════ 配置 ═══════════════
M1_RATE_LIMIT = 3                 # 统一限速器：每 tick 最多投递事件数（文档 rate≤3）
M1_CHUNK_SIZE = 1800              # 超长文本分片大小（字符）
M1_IDLE_TRIGGER_TICKS = 20        # 空闲定时：每 N tick 触发一次定向深耕（仅在有深耕队列时）
M1_WEB_TIMEOUT = 15               # 网络抓取超时（秒）
M1_CURSOR_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "m1_knowledge_cursor.json"

# ═══════════════ 统一限速器（防事件洪水，文档风险清单第1条关联） ═══════════════
class _RateLimiter:
    """按 tick 窗口限速：每个 tick 最多投 rate 条，超出的排队到下一 tick。"""

    def __init__(self, rate: int = M1_RATE_LIMIT):
        self.rate = max(1, int(rate))
        self._quota = self.rate
        self._last_tick = -1

    def try_acquire(self, tick: int) -> bool:
        """当前 tick 是否还有额度。tick 变化时重置额度。"""
        if tick != self._last_tick:
            self._last_tick = tick
            self._quota = self.rate
        if self._quota <= 0:
            return False
        self._quota -= 1
        return True


# ═══════════════ 知识包持久化队列（游标续读 + 记忆去重） ═══════════════
class KnowledgePackageQueue:
    """途径2：预制知识包导入队列。

    - 每条条目带唯一 item_id；
    - 持久化游标：processed_ids（已投递）+ pending（待投递），重启续读；
    - 记忆去重：投递前检查「已投递集合」与「长期记忆库中是否已有同 item_id」，防重复灌入。"""

    def __init__(self, cursor_path: Path = M1_CURSOR_PATH):
        self.cursor_path = cursor_path
        self.processed_ids: set = set()
        self.content_hashes: set = set()
        self.pending: List[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            if self.cursor_path.exists():
                raw = json.loads(self.cursor_path.read_text(encoding="utf-8"))
                self.processed_ids = set(raw.get("processed_ids", []) or [])
                self.content_hashes = set(raw.get("content_hashes", []) or [])
                self.pending = raw.get("pending", []) or []
                self._migrate_pending()
        except Exception as e:
            logger.warning(f"[M1] 知识包游标加载失败（从空队列开始）: {e}")

    def _migrate_pending(self) -> None:
        """迁移旧队列：补 content_hash 并按内容去重（内容相同只留一条）。"""
        seen = set(self.content_hashes)
        kept: List[dict] = []
        for p in self.pending:
            if not isinstance(p, dict):
                continue
            content = str(p.get("content", "") or "")
            ch = p.get("content_hash") or self._content_hash(content)
            p["content_hash"] = ch
            if ch in seen:
                continue
            seen.add(ch)
            kept.append(p)
        self.pending = kept

    def _save(self) -> None:
        try:
            self.cursor_path.parent.mkdir(parents=True, exist_ok=True)
            self.cursor_path.write_text(
                json.dumps({"processed_ids": sorted(self.processed_ids),
                            "content_hashes": sorted(self.content_hashes),
                            "pending": self.pending,
                            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")},
                           ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"[M1] 知识包游标保存失败: {e}")

    @staticmethod
    def _content_hash(content: str) -> str:
        """内容级去重哈希：内容一模一样（字节级）则哈希一致，跨文件/位置去重。"""
        import hashlib
        return hashlib.md5(str(content or "").encode("utf-8")).hexdigest()

    def enqueue(self, entries: List[dict]) -> tuple:
        """批量入队，返回 (新增条数, 重复跳过条数)。

        去重规则（内容级优先）：内容一模一样（哈希一致）无论来自哪个文件/位置只存一条；
        其次按 item_id 来源级去重（兼容历史旧游标）。"""
        added = 0
        skipped = 0
        pending_hashes = {p.get("content_hash") for p in self.pending}
        for e in entries:
            if not isinstance(e, dict):
                skipped += 1
                continue
            content = str(e.get("content", "") or "")
            if not content.strip():
                skipped += 1
                continue
            ch = self._content_hash(content)
            iid = str(e.get("item_id", "") or "")
            if ch in self.content_hashes or ch in pending_hashes:
                skipped += 1
                continue
            if iid and iid in self.processed_ids:
                skipped += 1
                continue
            item = {"item_id": iid, "content": content, "content_hash": ch}
            self.pending.append(item)
            pending_hashes.add(ch)
            added += 1
        self._save()
        return added, skipped

    def pop_batch(self, n: int) -> List[dict]:
        """取最多 n 条待投递，并标记为已处理（游标前移）。"""
        batch = self.pending[:n]
        if batch:
            self.pending = self.pending[n:]
            for b in batch:
                if b.get("item_id"):
                    self.processed_ids.add(b["item_id"])
                self.content_hashes.add(b.get("content_hash") or self._content_hash(str(b.get("content", "") or "")))
            self._save()
        return batch


# ═══════════════ 网络抓取（标准库，自包含） ═══════════════
def _fetch_url(url: str, timeout: int = M1_WEB_TIMEOUT) -> Optional[str]:
    """抓取网页正文（纯文本提取，去标签）。失败返回 None。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "7Tan-M1/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # 简单去标签（正则提取正文，非完整 HTML 解析器，够用即可）
        import re
        text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", html, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text or None
    except Exception as e:
        logger.warning(f"[M1] 网络抓取失败 {url}: {e}")
        return None


# ═══════════════ 上层模块 M1 主体 ═══════════════
class UpperModuleM1:
    """阶段1 双知识获取体系。mount() 后通过 post_tick_hook 自主投递外部知识。"""

    def __init__(self, rate: int = M1_RATE_LIMIT):
        self.limiter = _RateLimiter(rate)
        self.pkg_queue = KnowledgePackageQueue()
        self._tick_seen = -1
        self._deep_queue: List[dict] = []     # 空闲定时深耕队列（web_fetch 待抓取）
        self._mounted = False

    # ── 挂载 ──
    def mount(self) -> bool:
        if self._mounted:
            return False
        if register_external_source is None:
            logger.warning("[M1] 内核只读接口不可用，挂载失败")
            return False
        register_external_source("web_fetch", "互联网自主学习")
        register_external_source("knowledge_package", "预制知识包导入")
        register_post_tick_hook(self._on_tick)
        self._mounted = True
        logger.info("[M1] 双知识获取体系已挂载（post_tick_hook + web_fetch/knowledge_package 来源登记）")
        return True

    # ── 对外接口：互联网自学 ──
    def learn_from_web(self, url: str, trigger: str = "manual") -> int:
        """抓取一个 URL，分片后排队投递（source=web_fetch）。返回排队片段数。"""
        text = _fetch_url(url)
        if not text:
            # 获取失败同样封装事件存入记忆，优化后续学习策略（文档要求）
            self._emit_fetch_failure(url)
            return 0
        chunks = self._chunk(text)
        for c in chunks:
            self._deep_queue.append({"url": url, "chunk": c, "trigger": trigger})
        return len(chunks)

    def import_knowledge_package(self, entries: List[dict]) -> dict:
        """导入预制知识包（source=knowledge_package）。返回 {added, skipped, pending}。"""
        added, skipped = self.pkg_queue.enqueue(entries)
        return {"added": added, "skipped": skipped, "pending": len(self.pkg_queue.pending)}

    def drain_now(self, max_batch: int = M1_RATE_LIMIT) -> int:
        """手动导入后立即投递一批 pending（遵守单批额度，立即执行，不等心跳 tick）。

        用户主动导入知识包时调用，让知识即时可见；仍按单批 3 条投递，
        不破坏「防事件洪水」约束（批量导入走队列，逐 tick 消化剩余）。"""
        batch = self.pkg_queue.pop_batch(max_batch)
        n = 0
        for item in batch:
            self._emit_knowledge(item["item_id"], item["content"])
            n += 1
        return n

    def drain_all(self) -> int:
        """⚡ 立即学习全部：一次性把队列所有 pending 直接写入长期记忆库（memory_library），
        绕过 12 格工作记忆瓶颈（方案 A：知识包直达长期记忆）。

        用户手动触发，跳过 rate≤3 限速。知识内容不再走 tool_result 事件链路（避免被
        工作记忆 12 格上限挤出导致内容丢失），而是直接 append 进 memory_library 并立即
        落盘。日常 tick 的 _drain_package_queue 仍走标准心智链路（少量、安全）。"""
        batch = self.pkg_queue.pop_batch(len(self.pkg_queue.pending))
        n = 0
        subj = float((subjective_time or {}).get("subjective_clock", 0.0) or 0.0)
        for item in batch:
            content = str(item.get("content", "") or "").strip()
            if not content:
                continue
            memory_library.append({
                "thought": content[:M1_CHUNK_SIZE],
                "focus": 0.5,
                "valence": 0.1,
                "origin": "external",
                "subjective_time": subj,
                "weight_eff": 1.0,
                "goal_tag": f"知识包:{str(item.get('item_id', ''))[:16]}",
                "pe": 0.0,
                "success": None,
            })
            n += 1
        # 控制长期记忆库规模（与 module_a_tick 一致：按 weight_eff 最低淘汰，保护高权重记忆）
        while len(memory_library) > 200:
            if len(memory_library) <= 1:
                break
            _worst_i = min(
                range(len(memory_library)),
                key=lambda i: (float(memory_library[i].get("weight_eff", 1.0) or 0.0)
                               if isinstance(memory_library[i], dict) else -1.0),
            )
            memory_library.pop(_worst_i)
        # 立即落盘，确保知识真正写入记忆库文件
        if save_organ_state is not None:
            try:
                save_organ_state()
            except Exception as e:
                logger.warning(f"[M1] 知识直达长期记忆后落盘失败: {e}")
        return n

    # ── post_tick_hook：每 tick 限速投递 ──
    def _on_tick(self) -> None:
        try:
            tick = self._current_tick()
            if tick == self._tick_seen:
                return
            self._tick_seen = tick
            # 1) 知识包队列优先（游标续读 + 去重）
            self._drain_package_queue()
            # 2) 互联网自学（空闲定时深耕）
            self._drain_deep_queue()
        except Exception as e:
            logger.warning(f"[M1] tick 钩子异常: {e}")

    def _drain_package_queue(self) -> None:
        batch = self.pkg_queue.pop_batch(M1_RATE_LIMIT)
        for item in batch:
            if not self.limiter.try_acquire(self._current_tick()):
                # 额度耗尽：回退（重新入队，下一 tick 再投）
                self.pkg_queue.pending.insert(0, item)
                break
            self._emit_knowledge(item["item_id"], item["content"])

    def _drain_deep_queue(self) -> None:
        # 空闲定时深耕：仅在无知识包挤压时，每 M1_IDLE_TRIGGER_TICKS tick 投 1 条
        tick = self._current_tick()
        if tick % M1_IDLE_TRIGGER_TICKS != 0:
            return
        if not self._deep_queue:
            return
        if not self.limiter.try_acquire(tick):
            return
        item = self._deep_queue.pop(0)
        self._emit_web(item["url"], item["chunk"], item.get("trigger", "idle"))

    # ── 事件投递（统一 tool_result，source 区分，遵 C5） ──
    def _emit_knowledge(self, item_id: str, content: str) -> None:
        if emit_event is None:
            return
        emit_event(
            "tool_result",
            payload={"tool": "knowledge_package", "ok": True, "item_id": item_id,
                     "thought_fragment": content[:M1_CHUNK_SIZE],
                     "goal_tag": f"知识包:{item_id[:16]}"},
            source="knowledge_package",
            origin="external",
        )

    def _emit_web(self, url: str, chunk: str, trigger: str) -> None:
        if emit_event is None:
            return
        emit_event(
            "tool_result",
            payload={"tool": "web_fetch", "ok": True, "url": url, "trigger": trigger,
                     "thought_fragment": chunk,
                     "goal_tag": f"自学:{urllib.parse.urlparse(url).netloc[:24]}"},
            source="web_fetch",
            origin="external",
        )

    def _emit_fetch_failure(self, url: str) -> None:
        if emit_event is None:
            return
        emit_event(
            "tool_result",
            payload={"tool": "web_fetch", "ok": False, "url": url,
                     "thought_fragment": f"网络抓取失败：{url}",
                     "goal_tag": "自学失败"},
            source="web_fetch",
            origin="external",
        )

    # ── 工具函数 ──
    @staticmethod
    def _chunk(text: str) -> List[str]:
        return [text[i:i + M1_CHUNK_SIZE] for i in range(0, len(text), M1_CHUNK_SIZE)]

    @staticmethod
    def _current_tick() -> int:
        try:
            import src.agent.bionic_organs as bo
            return int(getattr(bo, "_organ_tick_counter", 0))
        except Exception:
            return 0


# ═══════════════ 模块级单例（供 main.py / 上层装配器调用） ═══════════════
_m1_instance: Optional[UpperModuleM1] = None


def get_m1() -> UpperModuleM1:
    global _m1_instance
    if _m1_instance is None:
        _m1_instance = UpperModuleM1()
    return _m1_instance


def mount_m1() -> bool:
    """一键挂载 M1（幂等）。在应用启动时调用一次。"""
    return get_m1().mount()


if __name__ == "__main__":
    m1 = get_m1()
    print("挂载:", m1.mount())
    print("登记外部来源:", ["web_fetch", "knowledge_package"])
    print("导入知识包测试:", m1.import_knowledge_package([
        {"item_id": "kp-001", "content": "示例知识条目一"},
        {"item_id": "kp-002", "content": "示例知识条目二"},
        {"item_id": "kp-001", "content": "重复条目（应被去重）"},
    ]), "条（去重后）")
    print("待投递队列长度:", len(m1.pkg_queue.pending))
