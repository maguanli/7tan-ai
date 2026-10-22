"""
消息序列守卫 — 双向修复「孤儿 tool 消息」，防止 OpenAI 兼容 API 返回 400

API 对 tool 消息有两条硬性约束（双向）：
  ① assistant 声明的每个 tool_call，后面必须紧跟一条 role=tool 的响应；
  ② 每条 role=tool 的消息，必须能对应到前面某条 assistant 声明的 tool_call_id。

只要历史在「assistant(带 tool_calls) ↔ 它的 tool 响应」之间被切断，就会产生
两类孤儿，任一残留都会触发 400：

  孤儿 tool_calls（正向）
      assistant 带 tool_calls，但后面没有 tool 响应
      → Messages with role 'assistant' ... tool_calls must be followed by tool messages

  孤儿 tool 响应（反向）  ← 本次新增修复的一类
      role=tool，但前面找不到声明它的 assistant
      → Messages with role 'tool' must be a response to a preceding message with 'tool_calls'

实现要点：**按索引配对，不按集合配对**。
    只用「id 是否出现过」做判断会漏掉位置信息 —— 例如 tool 响应出现在声明之前、
    或同一 id 被多条 assistant 重复声明时，都会误判为合法。这里为每个 id 计算
    「唯一属主」：响应归给它前面最近的那条声明（严格 1:1），双方位置不匹配的一律剔除。

切断的三个真实来源：
  · ContextManager._trim_if_needed() 按条数切片（self.history[-N:]），切口落在配对中间
  · 任务被中途终止（用户点终止 / 超时 / 防并发保护），tool 结果还没写回
  · _cleanup_ctx_on_abort() 把含 tool 消息的 messages 写回 ctx.history，
    下一轮又被当作历史重新发送

本模块是唯一的序列规范化实现，由两处共同引用：
  · agent_loop._repair_messages()  —— Agent 循环内，请求前修一次
  · model_manager.chat()           —— 所有 LLM 调用的最终兜底
"""
from loguru import logger


def _tc_id(tc) -> str:
    """取 tool_call 的 id，兼容 dict 与 SDK 对象两种形态。"""
    if isinstance(tc, dict):
        return tc.get("id") or ""
    return getattr(tc, "id", "") or ""


def sanitize_tool_messages(messages: list, label: str = "") -> list:
    """双向清洗消息序列，移除所有孤儿 tool 消息。

    规则（严格 1:1 配对）：
      · 每个 tool_call_id 的响应归给「它前面最近的那条声明」，且只保留第一条
        位置合法的响应；其余响应剔除；
      · assistant 的 tool_calls 只保留「属主是它自己」的那些；若一个都不剩，
        则退化成普通 assistant 文本（content 为空则整条丢弃）；
        此时必须一并去掉 reasoning_content —— 该字段仅在带 tool_calls 时合法。

    Args:
        messages: 待清洗的消息列表（不原地修改，返回新列表）
        label: 日志标识，用于定位污染来源

    Returns:
        List[dict]: 清洗后的消息列表
    """
    if not messages:
        return messages

    # ① 每条 id 的声明位置（升序）与响应位置（升序）
    decl_positions = {}
    resp_positions = {}
    for idx, msg in enumerate(messages):
        role = msg.get("role")
        if role == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                tid = _tc_id(tc)
                if tid:
                    decl_positions.setdefault(tid, []).append(idx)
        elif role == "tool":
            tid = msg.get("tool_call_id") or ""
            if tid:
                resp_positions.setdefault(tid, []).append(idx)

    # ② 为每个 id 选出唯一属主：(响应索引, 声明索引)
    #    响应必须排在某条声明之后；取「最近的那条声明」作为属主，保证 1:1
    owner = {}   # tid -> (resp_idx, decl_idx)
    for tid, resps in resp_positions.items():
        decls = decl_positions.get(tid, [])
        if not decls:
            continue
        for j in resps:
            priors = [d for d in decls if d < j]
            if priors:
                owner[tid] = (j, max(priors))
                break

    dropped_tool = 0
    dropped_assistant = 0
    trimmed = 0
    out = []

    for idx, msg in enumerate(messages):
        role = msg.get("role")

        if role == "tool":
            tid = msg.get("tool_call_id") or ""
            own = owner.get(tid)
            if own is not None and own[0] == idx:
                out.append(msg)
            else:
                dropped_tool += 1
            continue

        if role == "assistant" and msg.get("tool_calls"):
            kept = [tc for tc in msg["tool_calls"]
                    if owner.get(_tc_id(tc)) is not None
                    and owner[_tc_id(tc)][1] == idx
                    and owner[_tc_id(tc)][0] > idx]
            if len(kept) == len(msg["tool_calls"]):
                out.append(msg)
            elif kept:
                new_msg = dict(msg)
                new_msg["tool_calls"] = kept
                out.append(new_msg)
                trimmed += 1
            else:
                content = (msg.get("content") or "").strip()
                if content:
                    out.append({k: v for k, v in msg.items()
                                if k not in ("tool_calls", "reasoning_content")})
                dropped_assistant += 1
            continue

        out.append(msg)

    if dropped_tool or dropped_assistant or trimmed:
        tag = f"[{label}]" if label else ""
        logger.warning(
            f"🧹 消息序列修复{tag} 剔除孤儿 tool 响应 {dropped_tool} 条 / "
            f"无响应 tool_calls 的 assistant {dropped_assistant} 条 / "
            f"裁剪 tool_calls {trimmed} 条（{len(messages)} → {len(out)} 条）"
        )

    return out


# ============================================================
# 上下文预算守卫（2026-10-23 新增）
# ============================================================
# 事故背景：会话 a5502176 里有一条 assistant 消息正文长达 9,364,943 字符
# （把记忆库 76529 段经历整篇倾倒），ContextManager 按「条数」截断（保留 50 条）
# 根本不看体积 → 整条 9.3MB 消息原样发给 API → 请求体约 436 万 tokens，
# 直接 400「maximum context length is 1048576 tokens」，AI 一路报错无法回复。
#
# 本守卫是「体积维度」的最后一道闸：
#   ① 单条消息硬截断（默认 24000 字符，头 60% + 尾 40% 保留上下文线索）
#   ② 总量超预算时，保留全部 system + 最近的连续消息，丢弃更旧的消息
#   ③ 丢弃后再跑一次 sanitize_tool_messages，避免切出孤儿 tool 消息
# 位置：model_manager.chat() 内（所有 LLM 调用的最终出口）。

import json as _json

DEFAULT_MAX_TOKENS = 300_000          # 单次请求允许的上下文 token 上限
DEFAULT_MAX_MESSAGE_CHARS = 24_000    # 单条消息正文上限（约 12000 tokens）


def _msg_chars(msg) -> int:
    """估算单条消息的字符数（content + tool_calls 序列化）。"""
    if not isinstance(msg, dict):
        return len(str(msg))
    total = len(msg.get("content") or "")
    tcs = msg.get("tool_calls")
    if tcs:
        try:
            total += len(_json.dumps(tcs, ensure_ascii=False))
        except Exception:
            total += 200 * len(tcs)
    return total


def estimate_messages_tokens(messages: list) -> int:
    """粗略估算消息列表的 token 数（经验值：约 2 字符 = 1 token）。"""
    return sum(_msg_chars(m) for m in messages) // 2


def truncate_text(text: str, limit: int) -> str:
    """保留头部 60% + 尾部 40%，中间插入截断标记。"""
    if limit <= 0 or len(text) <= limit:
        return text
    marker = f"\n\n…[内容过长，已截断 {len(text) - limit} 字符]…\n\n"
    head = int(limit * 0.6)
    tail = max(0, limit - head - len(marker))
    return text[:head] + marker + (text[-tail:] if tail else "")


def enforce_context_budget(messages: list, max_tokens: int = DEFAULT_MAX_TOKENS,
                          max_message_chars: int = DEFAULT_MAX_MESSAGE_CHARS,
                          label: str = "") -> list:
    """按「体积」裁剪消息，保证请求不超模型上下文上限。

    Args:
        messages: 原始消息列表（dict 形态）
        max_tokens: 允许的最大 token 估算值
        max_message_chars: 单条消息正文上限
        label: 日志标识

    Returns:
        List[dict]: 裁剪后的消息列表（未超限时原样返回）
    """
    if not messages:
        return messages

    msgs = [dict(m) if isinstance(m, dict) else m for m in messages]

    # ① 单条硬截断
    truncated = 0
    for m in msgs:
        if not isinstance(m, dict):
            continue
        c = m.get("content")
        if isinstance(c, str) and len(c) > max_message_chars:
            m["content"] = truncate_text(c, max_message_chars)
            truncated += 1

    total = estimate_messages_tokens(msgs)
    if total <= max_tokens and not truncated:
        return msgs if msgs is not messages else messages

    if total <= max_tokens:
        tag = f"[{label}]" if label else ""
        logger.warning(f"✂️ 上下文守卫{tag} 硬截断超长消息 {truncated} 条，估算 {total} tokens")
        return sanitize_tool_messages(msgs, label=label or "budget")

    # ② 保 system + 最近的连续消息
    sys_idx = [i for i, m in enumerate(msgs) if isinstance(m, dict) and m.get("role") == "system"]
    sys_set = set(sys_idx)
    other_idx = [i for i in range(len(msgs)) if i not in sys_set]

    used = sum(_msg_chars(msgs[i]) for i in sys_idx) // 2
    kept = []
    for i in reversed(other_idx):
        t = _msg_chars(msgs[i]) // 2
        if kept and used + t > max_tokens:
            break
        kept.append(i)
        used += t
    kept.reverse()

    out = [msgs[i] for i in sorted(sys_set | set(kept))]
    out = sanitize_tool_messages(out, label=label or "budget")

    tag = f"[{label}]" if label else ""
    logger.warning(
        f"✂️ 上下文守卫{tag} 超预算裁剪：{len(messages)} → {len(out)} 条，"
        f"估算 {total} → {estimate_messages_tokens(out)} tokens"
        f"（上限 {max_tokens}，硬截断 {truncated} 条）"
    )
    return out
