# -*- coding: utf-8 -*-
"""
易经占卦插件 — 接入 D:\\7tan\\iching 独立项目
工具: iching_divine(起卦+AI解读), iching_query(卦象/爻辞/易传查询)
"""
import os
import sys

ICHING_DIR = r"D:\7tan\iching"
ICHING_PARENT = r"D:\7tan"  # import iching 需要父目录在 sys.path
for _p in (ICHING_PARENT, ICHING_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.tools.registry import register_tool


@register_tool(
    name="iching_divine",
    description="易经占卦：金钱卦/数字卦/时间卦起卦，并自动附上卦辞、爻辞、彖传、象传原文，可选 DeepSeek 白话解读。用户说'帮我占一卦/起一卦'时使用。",
    parameters={
        "type": "object",
        "properties": {
            "method": {"type": "string", "description": "起卦方式: coin(金钱卦)/num(数字卦)/time(时间卦)", "default": "coin"},
            "nums": {"type": "string", "description": "数字卦的三个数（逗号分隔，如 3,5,7），method=num 时必填", "default": ""},
            "question": {"type": "string", "description": "所占之事/问题", "default": ""},
            "use_llm": {"type": "boolean", "description": "是否调用 DeepSeek 生成白话解读", "default": True},
        },
        "required": ["question"],
    },
    category="iching"
)
def iching_divine(method: str = "coin", nums: str = "", question: str = "",
                  use_llm: bool = True) -> str:
    """起卦 + 可选 AI 白话解读"""
    try:
        from iching.engine import cast, render
        if method == "num" and nums:
            a, b, c = [int(x.strip()) for x in nums.split(",")[:3]]
            result = cast("num", a=a, b=b, c=c)
        elif method == "time":
            result = cast("time")
        else:
            result = cast("coin")
        text = render(result)
        if use_llm:
            from iching.llm import interpret
            try:
                llm_text = interpret(
                    f"{text}\n\n所占问题：{question or '（未说明）'}",
                    gua_name=result["name"], question=question)
                text += "\n\n── AI 白话解读 ──\n" + llm_text
            except Exception as e:
                text += f"\n（AI 解读暂不可用：{e}）"
        return text
    except Exception as e:
        return f"❌ 占卦失败: {e}"


@register_tool(
    name="iching_query",
    description="查询易经知识：按卦名查卦辞/六爻爻辞/彖传/大象传，或按关键词检索相关卦象。用于解读经典、查卦资料。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "卦名，如 '乾'、'既济'；不填则按关键词检索", "default": ""},
            "keyword": {"type": "string", "description": "关键词检索（如 '自强不息'、'潜龙勿用'），name 为空时使用", "default": ""},
        },
        "required": [],
    },
    category="iching"
)
def iching_query(name: str = "", keyword: str = "") -> str:
    """查卦/查知识"""
    try:
        from iching.data import get_gua_by_name, YICI
        from iching.rag import get_originals, search
        if name:
            g = get_gua_by_name(name)
            if not g:
                return f"❌ 无此卦: {name}"
            no, nm, up, down, gui = g
            lines = [f"📖 {no} {nm}卦（{down}下{up}上）", f"卦辞：{gui}"]
            for i, y in enumerate(YICI.get(nm, []), 1):
                lines.append(f"  {y}")
            orig = get_originals(nm)
            if orig["tuan"]:
                lines.append(f"彖传：{orig['tuan']}")
            if orig["xiang"]:
                lines.append(f"大象传：{orig['xiang']}")
            return "\n".join(lines)
        if keyword:
            hits = search(keyword, top_k=5)
            if not hits:
                return f"未检索到与「{keyword}」相关的卦象。"
            lines = [f"🔍 与「{keyword}」相关的卦："]
            for h in hits:
                lines.append(f"· {h['no']} {h['name']}卦 大象传：{h['xiang']}")
            return "\n".join(lines)
        return "请提供卦名（如 name='乾'）或检索关键词（keyword）。"
    except Exception as e:
        return f"❌ 查询失败: {e}"
