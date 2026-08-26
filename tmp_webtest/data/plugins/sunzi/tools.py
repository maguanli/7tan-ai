# -*- coding: utf-8 -*-
"""
孙子兵法插件 — 接入 D:\\7tan\\sunzi 独立知识库项目
工具: sunzi_ask(兵法问答), sunzi_strategy(决策推演), sunzi_chapter(篇章查询), sunzi_daily(每日兵法)
让 7Tan 拥有孙子兵法的智慧：先谋后动、避实击虚、知彼知己。
"""
import os
import sys

# 只需父目录 D:\\7tan 在 sys.path 即可 import sunzi 包（绝不能把 D:\\7tan\\sunzi 放进 sys.path，
# 其 data.py 会劫持顶层模块名 data，导致 from data.plugins.xxx 导入失败）
SUNZI_PARENT = r"D:\7tan"
if SUNZI_PARENT not in sys.path:
    sys.path.append(SUNZI_PARENT)  # append 放末尾，不抢占其他模块

from src.tools.registry import register_tool


@register_tool(
    name="sunzi_ask",
    description="孙子兵法问答：用《孙子兵法》的智慧回答用户的问题（商业竞争/职场博弈/人生决策等）。自动检索十三篇原文佐证，由 DeepSeek 结合兵法给出论断、依据、现代应用与行动建议。用户提到'兵法/孙子/谋略'类问题时使用。",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "要咨询的问题或处境描述", "default": ""},
        },
        "required": ["question"],
    },
    category="sunzi"
)
def sunzi_ask(question: str = "") -> str:
    """兵法问答：RAG 检索 + DeepSeek 解读"""
    if not question.strip():
        return "请提供要咨询的问题，例如：对手降价促销，我该怎么应对？"
    try:
        from sunzi.rag import build_knowledge_section, search
        from sunzi.data import knowledge_status
        # 本地先给出命中篇章概览（即使 LLM 失败也有基础答案）
        hits = search(question, top_k=3)
        local = ["🔍 命中的兵法篇章："]
        for h in hits:
            local.append(f"· 第{h['no']}篇《{h['name']}》（匹配度 {h['score']}）")
        try:
            from sunzi.llm import interpret
            llm_text = interpret(question, mode="ask", question=question)
            return f"{'、'.join(local)}\n\n── 兵法智慧解读 ──\n{llm_text}"
        except Exception as e:
            # LLM 失败：本地知识兜底
            section = build_knowledge_section(question, top_k=2, max_len=1500)
            return f"{'、'.join(local)}\n（AI 深度解读暂不可用：{e}）\n\n【原文参考】\n{section}"
    except Exception as e:
        return f"❌ 兵法问答失败: {e}"


@register_tool(
    name="sunzi_strategy",
    description="孙子兵法决策推演：用户描述一个处境（商业竞争/职场博弈/重要选择），AI 用兵法框架提炼敌我势时地要素、匹配兵法原理、给出主策略+备选方案+风险提示。用户说'用兵法帮我分析/出个主意/推演'时使用。",
    parameters={
        "type": "object",
        "properties": {
            "situation": {"type": "string", "description": "处境描述（越具体越好：对手、资源、时机、目标）", "default": ""},
        },
        "required": ["situation"],
    },
    category="sunzi"
)
def sunzi_strategy(situation: str = "") -> str:
    """决策推演：兵法框架下的策略建议"""
    if not situation.strip():
        return "请描述你的处境，例如：我在跟竞争对手抢同一个客户，对方报价比我低30%，我该怎么办？"
    try:
        from sunzi.llm import interpret
        llm_text = interpret(situation, mode="strategy", question=situation)
        return f"── 兵法决策推演 ──\n{llm_text}"
    except Exception as e:
        # LLM 失败：本地检索兜底
        try:
            from sunzi.rag import build_knowledge_section
            section = build_knowledge_section(situation, top_k=3, max_len=2000)
            return f"（AI 深度推演暂不可用：{e}）\n\n【相关兵法原文参考，请自行对照】\n{section}"
        except Exception as e2:
            return f"❌ 决策推演失败: {e2}"


@register_tool(
    name="sunzi_chapter",
    description="查询《孙子兵法》篇章：按编号（1-13）或篇名（如'谋攻'、'虚实'）返回该篇完整内容：原文+白话译文+核心思想+名句+应用案例。用户说'看看兵法某篇/孙子兵法第几篇'时使用。",
    parameters={
        "type": "object",
        "properties": {
            "chapter": {"type": "string", "description": "篇名或编号，如 '谋攻'、'虚实'、'7'、'第3篇'", "default": ""},
            "include_modern": {"type": "boolean", "description": "是否包含白话译文", "default": True},
        },
        "required": ["chapter"],
    },
    category="sunzi"
)
def sunzi_chapter(chapter: str = "", include_modern: bool = True) -> str:
    """篇章查询：本地直接输出，无需 LLM"""
    if not chapter.strip():
        try:
            from sunzi.data import knowledge_status
            st = knowledge_status()
            return "📖 《孙子兵法》十三篇：\n" + "\n".join(
                f"  {t}" for t in st["titles"]) + "\n\n输入篇名或编号查询详情，如 sunzi_chapter(chapter='谋攻')"
        except Exception as e:
            return f"❌ 查询失败: {e}"
    try:
        from sunzi.rag import build_chapter_section
        text = build_chapter_section(chapter, include_modern=include_modern)
        if not text:
            return f"❌ 未找到篇章: {chapter}（可用编号1-13或篇名，如'谋攻'）"
        return text
    except Exception as e:
        return f"❌ 查询失败: {e}"


@register_tool(
    name="sunzi_daily",
    description="每日兵法：以日期为种子确定性地从《孙子兵法》十三篇中选一篇（同一天所有人得到同一篇），返回该篇核心思想与名句，可选 DeepSeek 当日指引。用户问'今天的兵法/每日兵法/今天该读哪篇兵法'时使用。",
    parameters={
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "日期 YYYY-MM-DD（默认今天）", "default": ""},
            "use_llm": {"type": "boolean", "description": "是否调用 DeepSeek 生成当日指引", "default": False},
        },
        "required": [],
    },
    category="sunzi"
)
def sunzi_daily(date: str = "", use_llm: bool = False) -> str:
    """每日兵法：日期种子确定性选篇"""
    try:
        from datetime import datetime
        from sunzi.data import get_chapters, get_chapter
        date = (date or datetime.now().strftime("%Y-%m-%d")).strip()
        seed = int(date.replace("-", ""))
        no = seed % 13 + 1  # 1-13
        ch = get_chapter(no)
        if not ch:
            return f"❌ 每日兵法失败: 未找到第{no}篇"
        lines = [f"⚔️ 今日兵法（{date}）· 第{ch['no']}篇《{ch['name']}》"]
        if ch.get("title"):
            lines.append(f"篇旨：{ch['title']}")
        core = ch.get("core", [])
        if core:
            lines.append("\n【核心思想】\n" + "\n".join(f"· {c}" for c in core))
        quotes = ch.get("quotes", [])
        if quotes:
            lines.append("\n【今日名句】")
            for q in quotes[:2]:
                lines.append(f"· {q['text']}")
                lines.append(f"  —— {q['trans']}")
        if use_llm:
            try:
                from sunzi.llm import interpret
                text = f"今日兵法为第{ch['no']}篇《{ch['name']}》：{'；'.join(core[:3])}"
                llm_text = interpret(text, mode="daily", question=f"{date} 每日兵法指引")
                lines.append(f"\n── AI 当日指引 ──\n{llm_text}")
            except Exception as e:
                lines.append(f"\n（AI 指引暂不可用：{e}）")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 每日兵法失败: {e}"
