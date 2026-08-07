# -*- coding: utf-8 -*-
"""
爆款文章工坊插件 — 爆款方法论 + DeepSeek 深度推理，一站式产出高传播公众号文章
工具:
  viral_topic    爆款选题生成（情绪价值评分，选题决定 70% 成败）
  viral_title    爆款标题生成（10 个备选 + 类型 + 打开率预测）
  viral_outline  爆款大纲生成（钩子/故事/转折/升华/互动 五段式）
  viral_write    爆款正文撰写（故事+观点+金句，口语化有画面感）
  viral_quotes   金句卡片文案（提取/生成 6 条金句，供配图）
  viral_check    发布前质量检查（标题/字数/结构/敏感词/完读建议）

方法论（内置系统提示词）：
  爆款 = 70% 选题 + 20% 标题 + 10% 内容
  选题抓情绪：共鸣 / 身份认同 / 焦虑痛点 / 好奇悬念 / 利益相关
  标题四式：数字具象、悬念反差、身份代入、场景共鸣
  结构五段：钩子开头(3秒留人) → 故事推进 → 观点金句 → 情绪升华 → 互动引导
  语言：口语化、短句、有画面感、多用比喻
"""
import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

# ─── 付费授权模块（license.py 按文件加载，避免包结构依赖）───
def _load_license_mod():
    import importlib.util
    _lic_path = Path(__file__).resolve().parent / "license.py"
    spec = importlib.util.spec_from_file_location("viral_writer_license", _lic_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_LIC = _load_license_mod()


def _gate():
    """付费闸门：已激活 / 试用中放行，否则返回购买引导"""
    allowed, msg = _LIC.check_access()
    return allowed, msg

# ─── 爆款方法论系统提示词 ───
SYSTEM_PROMPT = """你是公众号爆款文章专家，深谙新媒体传播规律，写过大量10w+文章。
铁律：
1. 爆款 = 70%选题 + 20%标题 + 10%内容，选题永远第一位
2. 选题抓情绪：共鸣(扎心)/身份认同(说的就是我)/焦虑痛点/好奇悬念/利益相关
3. 标题四式：数字具象(3个习惯)、悬念反差(越穷越要)、身份代入(40岁才懂)、场景共鸣(深夜的朋友圈)
4. 结构五段：钩子开头(前3秒留人)→故事推进(有细节有画面)→观点金句(短而有力)→情绪升华(让人转发)→互动引导(点赞在看评论)
5. 语言：口语化、短句、多用比喻、有画面感，像朋友聊天不像写作文
6. 只输出中文结果，直接给干货，不要解释方法论
7. 金句标准：一句话让人想截图、想转发、想收藏"""


def _llm(system_prompt: str, user_prompt: str, max_tokens: int = 2500,
         temperature: float = 0.9) -> str:
    """调用当前活跃 AI 模型（复用软件配置，零额外配置）；失败返回 None"""
    try:
        from openai import OpenAI
        from src.config.loader import get_active_ai_config
        cfg = get_active_ai_config()
        key = cfg.get("api_key", "")
        url = cfg.get("base_url", "https://api.deepseek.com/v1")
        model = cfg.get("model", "")
        if not key:
            return None
        client = OpenAI(api_key=key, base_url=url, timeout=90)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None


# ─────────────────── 1. 爆款选题 ───────────────────
@register_tool(
    name="viral_topic",
    description="爆款选题生成：根据公众号定位/关键词生成 10 个爆款选题，每个带情绪价值类型、目标人群、爆款潜力分(1-10)和理由。选题决定文章 70% 成败，写文章前先用它。",
    parameters={
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "主题/关键词，如：中年人生、育儿、赚钱、健康、情感", "default": ""},
            "audience": {"type": "string", "description": "目标人群，如：30-45岁中年人、宝妈、职场人", "default": "普通大众"},
            "count": {"type": "integer", "description": "生成选题数量", "default": 10},
        },
        "required": ["keyword"],
    },
    category="viral",
)
def viral_topic(keyword: str = "", audience: str = "普通大众", count: int = 10) -> str:
    """爆款选题生成"""
    _gate_ok, _gate_msg = _gate()
    if not _gate_ok:
        return _gate_msg
    if not keyword.strip():
        return "请提供主题/关键词，例如 viral_topic(keyword='中年人的体面')"
    prompt = (f"围绕「{keyword}」为目标人群「{audience}」生成 {count} 个公众号爆款选题。\n"
              f"每个选题输出格式：\n"
              f"[序号] 《选题标题雏形》\n"
              f"    情绪价值: 共鸣/身份认同/焦虑/好奇/利益（选其一，说明戳中什么）\n"
              f"    目标人群: xxx\n"
              f"    爆款潜力: x.x/10（并一句话说明理由）\n"
              f"选题要覆盖不同情绪类型，避免同质化。")
    text = _llm(SYSTEM_PROMPT, prompt, max_tokens=3000, temperature=1.0)
    if text:
        return f"🔥 爆款选题 {count} 个（面向：{audience}）\n\n{text}\n\n💡 提示：选题分最高的 2-3 个优先写，可继续用 viral_title 生成标题。"
    # LLM 失败兜底：通用选题模板
    base = [
        f"《关于{keyword}，我劝你早点明白这 3 件事》",
        f"《{keyword}的人，后来都怎么样了？》",
        f"《40岁才明白，{keyword}才是人生最好的活法》",
        f"《那些{keyword}的人，早已悄悄戒掉了这 5 个习惯》",
        f"《如果重来一次，我一定不会这样{keyword}》",
        f"《深夜睡不着，才读懂{keyword}这三个字》",
        f"《{audience}最该看的{keyword}真相》",
        f"《我见过最{keyword}的人，不是有钱人》",
        f"《{keyword}，才是成年人最大的体面》",
        f"《关于{keyword}，这是我听过最好的答案》",
    ][:count]
    return (f"🔥 爆款选题 {count} 个（AI 深度生成暂不可用，给出通用模板）\n\n"
            + "\n".join(f"{i+1}. {t}" for i, t in enumerate(base))
            + "\n\n💡 提示：可重试获取 AI 深度选题，或直接继续用 viral_title 生成标题。")


# ─────────────────── 2. 爆款标题 ───────────────────
@register_tool(
    name="viral_title",
    description="爆款标题生成：根据文章主题生成 10 个爆款标题，每个带类型标签（数字/悬念/身份/场景/对比）和打开率预测。标题决定打开率，打开率决定推荐权重。",
    parameters={
        "type": "object",
        "properties": {
            "theme": {"type": "string", "description": "文章主题内容描述", "default": ""},
            "count": {"type": "integer", "description": "生成标题数量", "default": 10},
        },
        "required": ["theme"],
    },
    category="viral",
)
def viral_title(theme: str = "", count: int = 10) -> str:
    """爆款标题生成"""
    _gate_ok, _gate_msg = _gate()
    if not _gate_ok:
        return _gate_msg
    if not theme.strip():
        return "请提供文章主题，例如 viral_title(theme='中年人的体面和面子')"
    prompt = (f"根据主题「{theme}」生成 {count} 个公众号爆款标题。\n"
              f"要求：\n"
              f"1. 覆盖不同类型：数字型/悬念型/身份型/场景型/对比型至少各1个\n"
              f"2. 每个标题 ≤ 25 字，口语化，有情绪钩子\n"
              f"3. 输出格式：\n"
              f"[序号] 标题\n"
              f"    类型: 数字/悬念/身份/场景/对比\n"
              f"    打开率预测: 高/中高/中 + 一句话说明为什么吸引人")
    text = _llm(SYSTEM_PROMPT, prompt, max_tokens=2500, temperature=1.0)
    if text:
        return f"✍️ 爆款标题 {count} 个\n\n{text}\n\n💡 建议：打开率预测最高的 3 个 A/B 测试，或选最贴合内容的一个。"
    # 兜底模板
    bases = [
        (f"数字", f"关于{theme}，我总结了 3 个真相"),
        (f"悬念", f"{theme}？这是我听过最扎心的答案"),
        (f"身份", f"40岁以后，才真正读懂{theme}"),
        (f"场景", f"深夜一个人时，才明白{theme}的意义"),
        (f"对比", f"越是{theme}的人，越不急着证明自己"),
    ]
    out = []
    for i in range(min(count, 10)):
        t, s = bases[i % len(bases)]
        out.append(f"{i+1}. {s}\n    类型: {t}\n    打开率预测: 中高")
    return f"✍️ 爆款标题 {count} 个（AI 深度生成暂不可用，通用模板）\n\n" + "\n".join(out)


# ─────────────────── 3. 爆款大纲 ───────────────────
@register_tool(
    name="viral_outline",
    description="爆款大纲生成：根据选题生成五段式爆款结构大纲（钩子开头→故事推进→观点金句→情绪升华→互动引导），含每个小标题和写作要点。",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "选题/文章主题", "default": ""},
        },
        "required": ["topic"],
    },
    category="viral",
)
def viral_outline(topic: str = "") -> str:
    """爆款大纲生成"""
    _gate_ok, _gate_msg = _gate()
    if not _gate_ok:
        return _gate_msg
    if not topic.strip():
        return "请提供选题，例如 viral_outline(topic='40岁才明白，人生最好的活法是这四个字')"
    prompt = (f"为选题「{topic}」生成爆款五段式大纲。\n"
              f"格式：\n"
              f"📌 标题建议: （3个备选）\n"
              f"① 钩子开头(前3秒): 写作要点+示例开头\n"
              f"② 故事推进: 小标题+讲什么故事+埋什么细节\n"
              f"③ 观点金句: 2-3个核心观点+对应金句\n"
              f"④ 情绪升华: 如何拔高到人生/价值层面\n"
              f"⑤ 互动引导: 结尾如何引导点赞/在看/评论/转发")
    text = _llm(SYSTEM_PROMPT, prompt, max_tokens=2500, temperature=0.85)
    if text:
        return f"📐 爆款大纲：「{topic}」\n\n{text}\n\n💡 大纲确认后可继续用 viral_write 生成完整正文。"
    return (f"📐 爆款大纲：「{topic}」（AI 深度生成暂不可用，标准五段式）\n\n"
            f"① 钩子开头：反常识/扎心提问/场景代入，3秒留住读者\n"
            f"② 故事推进：讲 1-2 个身边人的具体故事，有细节有画面\n"
            f"③ 观点金句：提炼 2-3 个观点，每个配一句金句\n"
            f"④ 情绪升华：从个人故事升到普遍人生感悟\n"
            f"⑤ 互动引导：结尾提问/求点赞在看，引导评论区留言")


# ─────────────────── 4. 爆款正文 ───────────────────
@register_tool(
    name="viral_write",
    description="爆款正文撰写：根据选题+大纲生成完整文章正文（含小标题、金句、互动引导），口语化有画面感，可直接粘贴到公众号编辑器。",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "选题/文章主题", "default": ""},
            "outline": {"type": "string", "description": "大纲（可选，不填则自动生成）", "default": ""},
            "word_count": {"type": "integer", "description": "目标字数", "default": 1200},
        },
        "required": ["topic"],
    },
    category="viral",
)
def viral_write(topic: str = "", outline: str = "", word_count: int = 1200) -> str:
    """爆款正文撰写"""
    _gate_ok, _gate_msg = _gate()
    if not _gate_ok:
        return _gate_msg
    if not topic.strip():
        return "请提供选题，例如 viral_write(topic='40岁才明白，人生最好的活法是这四个字')"
    prompt = (f"根据选题「{topic}」写一篇 {word_count} 字左右的公众号爆款文章正文。\n"
              f"大纲参考（若有）：{outline[:1500] if outline else '自动按五段式结构'}\n"
              f"要求：\n"
              f"1. 五段式：钩子开头→故事推进→观点金句→情绪升华→互动引导\n"
              f"2. 口语化、短句、有画面感，像朋友聊天\n"
              f"3. 至少包含 3 个金句（用「」标出，方便后续做金句卡片）\n"
              f"4. 有具体人物故事细节，不要空谈道理\n"
              f"5. 正文用 ## 作为小标题分隔，段落之间用空行\n"
              f"6. 结尾引导点赞/在看/评论")
    text = _llm(SYSTEM_PROMPT, prompt, max_tokens=4000, temperature=0.95)
    if text:
        return f"📝 爆款正文：「{topic}」（约{word_count}字）\n\n{text}"
    return (f"📝 爆款正文：「{topic}」（AI 深度生成暂不可用，请稍后重试或用 viral_outline 先出大纲）\n\n"
            f"① 钩子：{topic}，这个问题的答案，藏在我两个朋友的故事里。\n\n"
            f"② 故事：发小的故事（细节+转折+感悟）……\n\n"
            f"③ 观点：**{topic}，才是成年人最大的清醒。**\n\n"
            f"④ 升华：人生没有白走的路，每一步都算数。\n\n"
            f"⑤ 互动：你身边有这样的故事吗？评论区聊聊。觉得有用，点个【在看】让更多人看到。")


# ─────────────────── 5. 金句卡片文案 ───────────────────
@register_tool(
    name="viral_quotes",
    description="金句卡片文案：从文章或主题中提取/生成 6 条金句（每条 20 字内，适合做成 1080x608 金句卡片配图），带排版建议和卡片标题。",
    parameters={
        "type": "object",
        "properties": {
            "article": {"type": "string", "description": "文章全文（或主题描述）", "default": ""},
        },
        "required": ["article"],
    },
    category="viral",
)
def viral_quotes(article: str = "") -> str:
    """金句卡片文案"""
    _gate_ok, _gate_msg = _gate()
    if not _gate_ok:
        return _gate_msg
    if not article.strip():
        return "请提供文章内容或主题，例如 viral_quotes(article='40岁才明白，人生最好的活法是……')"
    prompt = (f"从以下文章/主题中提取并润色 6 条金句，每条 ≤ 20 字，适合做成金句卡片配图。\n"
              f"输出格式：\n"
              f"[1] 金句内容\n"
              f"    卡片标题: 2-4字（如：体面/清醒/活着）\n"
              f"    场景: 放文章开头/结尾/第几段后\n\n"
              f"文章：\n{article[:3000]}")
    text = _llm(SYSTEM_PROMPT, prompt, max_tokens=1500, temperature=0.9)
    if text:
        return f"💬 金句卡片文案 6 条\n\n{text}\n\n💡 可继续用配图工具把金句做成 1080x608 卡片插入文章。"
    return ("💬 金句卡片文案 6 条（AI 深度生成暂不可用，通用模板）\n\n"
            "[1] 人生没有白走的路，每一步都算数。\n    卡片标题: 路\n    场景: 结尾\n"
            "[2] 真正成熟，是学会和自己和解。\n    卡片标题: 和解\n    场景: 第2段后\n"
            "[3] 你羡慕的生活，都是别人熬出来的。\n    卡片标题: 熬\n    场景: 第3段后\n"
            "[4] 最好的活法，是活成自己。\n    卡片标题: 自己\n    场景: 开头\n"
            "[5] 慢慢来，比较快。\n    卡片标题: 节奏\n    场景: 第4段后\n"
            "[6] 愿你起落有致，归来仍是少年。\n    卡片标题: 少年\n    场景: 结尾")


# ─────────────────── 6. 发布前检查 ───────────────────
@register_tool(
    name="viral_check",
    description="发布前质量检查：检查标题长度、正文长度、结构完整性（钩子/故事/金句/互动）、敏感词风险，输出修改建议。发布前必用。",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "文章标题", "default": ""},
            "content": {"type": "string", "description": "文章正文", "default": ""},
        },
        "required": ["title", "content"],
    },
    category="viral",
)
def viral_check(title: str = "", content: str = "") -> str:
    """发布前质量检查（本地规则，无需 LLM）"""
    _gate_ok, _gate_msg = _gate()
    if not _gate_ok:
        return _gate_msg
    issues, ok = [], []

    # 标题检查
    if title:
        n = len(title)
        if n > 64:
            issues.append(f"⚠️ 标题过长：{n} 字（公众号限 64 字）→ 建议精简到 25 字内")
        elif n > 25:
            ok.append(f"✅ 标题 {n} 字，未超限（建议 ≤25 字更抓眼）")
        else:
            ok.append(f"✅ 标题 {n} 字，长度合适")
        if not any(k in title for k in ["?", "？", "!", "！", ":", "：", "，", "、", "3", "5", "10", "40", "100"]):
            issues.append("💡 标题缺少数字/标点情绪钩子，可考虑 viral_title 优化")
    else:
        issues.append("❌ 标题为空！")

    # 正文检查
    text = content or ""
    n = len(text.replace("\n", "").replace(" ", ""))
    if n < 300:
        issues.append(f"❌ 正文过短：{n} 字（建议 ≥800 字，否则完读率和推荐权重低）")
    elif n < 800:
        issues.append(f"⚠️ 正文偏短：{n} 字（建议 1000-2000 字最佳）")
    else:
        ok.append(f"✅ 正文 {n} 字，长度适合")

    # 结构检查
    if text:
        if not any(k in text for k in ["？", "?", "为什么", "怎么", "吗"]):
            issues.append("💡 正文缺少提问/悬念元素，开头钩子可加强")
        if "我" in text and ("朋友" in text or "同事" in text or "同学" in text or "发小" in text):
            ok.append("✅ 有故事人物元素")
        else:
            issues.append("💡 建议加入具体人物故事（朋友/同事/亲戚），增强代入感")
        if "点赞" in text or "在看" in text or "评论" in text or "留言" in text or "关注" in text:
            ok.append("✅ 有互动引导")
        else:
            issues.append("💡 结尾缺少互动引导（点赞/在看/评论）")
        if "「" in text or "”" in text or '"' in text:
            ok.append("✅ 有金句/引语")
        else:
            issues.append("💡 缺少金句（用「」标出更利于做金句卡片）")

    # 敏感词快速预检
    risky = re.findall(r"(政治|领导|政府|国家|共产党|台湾|独立|分裂|暴乱|恐怖|死亡|自杀|赌博|贷款|投资|炒股|稳赚|包治|百分百|最|第一|国家级|绝对|史上)", text + title)
    if risky:
        issues.append(f"⚠️ 命中疑似敏感/违规词：{'、'.join(set(risky))}（发布前需用系统审核确认）")
    else:
        ok.append("✅ 未检出常见敏感词")

    report = ["📋 发布前检查报告\n"]
    report += ok if ok else []
    report += issues if issues else ["🎉 全部检查通过！"]
    score = max(0, 100 - len(issues) * 12)
    report.append(f"\n📊 综合评分：{score}/100" + ("（建议修改后发布）" if issues else "（可以发布！）"))
    return "\n".join(report)


# ─────────────────── 7. 激活 / 状态（免费工具）───────────────────
@register_tool(
    name="viral_activate",
    description="激活爆款写作插件：输入购买获得的授权码，激活后永久解锁全部功能（激活、状态查询不消耗试用次数）。",
    parameters={
        "type": "object",
        "properties": {
            "license_key": {"type": "string", "description": "购买获得的授权码", "default": ""},
        },
        "required": ["license_key"],
    },
    category="viral",
)
def viral_activate(license_key: str = "") -> str:
    """激活爆款写作插件"""
    if not license_key.strip():
        return (
            "请提供授权码，例如 viral_activate(license_key='xxxxxxxx.xxxxxxxx')\n\n"
            + _LIC.status_text()
        )
    ok, msg = _LIC.activate(license_key.strip())
    return msg


@register_tool(
    name="viral_status",
    description="查看爆款写作插件激活状态、免费试用剩余次数、本机指纹与购买方式。",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
    category="viral",
)
def viral_status() -> str:
    """查看激活状态与购买信息"""
    return _LIC.status_text()
