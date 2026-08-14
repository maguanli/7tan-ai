# -*- coding: utf-8 -*-
"""
爆款写作插件 v2.1 — 融入全网爆款写作方法论 + 微信搜一搜搜索流量优化（2026-08 升级）
搜一搜优化来源（微信官方《搜一搜优化教程01-04》+《快速入门》）：
  ① 标题：清晰、简洁、直接，直给信息（用户搜索词命中）；严禁标题党/文不对题
  ② 正文：一篇一主题、鲜明详实可用、完整不藏；严禁导流话术/隐藏文字/欺骗下载
  ③ 排版：突出重点和层次（小标题/加粗/列表/留白），图片可加载并配文字说明
  ④ 原创：优先声明原创；账号需持续运营、专注领域、完成认证
升级来源（网络搜集）：
  ① 金句7技法：神转折/押韵对仗/重复顶真/对比反差/反常语出惊人/仿写流行语/比喻类比
  ② 标题5大因素：话题争议/热点蹭流/痛点共鸣/好奇悬念/利益相关（九宫格命题招式）
  ③ 开头黄金三秒：反常识、扎心提问、场景代入、冲突前置、悬念预留、数据冲击、名人金句
  ④ 爆款总公式：爆款 = 强情绪 + 真细节 + 短节奏 + 好标题 + 强结构 + 高互动
  ⑤ SCQA 结构：情景(Situation)→冲突(Complication)→疑问(Question)→回答(Answer)
  ⑥ 结尾方法论：总结升华/金句收尾/互动引导/留白余味

工具:
  viral_topic    爆款选题生成（情绪价值评分，选题决定 70% 成败）
  viral_title    爆款标题生成（10 个备选 + 类型 + 打开率预测）
  viral_outline  爆款大纲生成（五段式 / SCQA 双结构可选）
  viral_write    爆款正文撰写（公式驱动 + 黄金三秒开头 + 金句技法）
  viral_quotes   金句卡片文案（按 7 大技法生成，供配图）
  viral_check    发布前质量检查（标题/字数/结构/金句/敏感词/搜一搜违规/完读建议）
  viral_soso     搜一搜搜索流量诊断（标题直给/正文完整/导流风险/原创，搜索流量版check）

方法论（内置系统提示词）：
  爆款 = 70% 选题 + 20% 标题 + 10% 内容
  爆款总公式 = 强情绪 + 真细节 + 短节奏 + 好标题 + 强结构 + 高互动
  选题抓情绪：共鸣 / 身份认同 / 焦虑痛点 / 好奇悬念 / 利益相关
  标题五因素：话题 / 热点 / 痛点 / 好奇 / 利益
  结构：五段式（钩子→故事→金句→升华→互动）或 SCQA
  语言：口语化、短句、有画面感、多用比喻
"""
import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

# ─── 爆款方法论系统提示词（v2.0：融入全网干货） ───
SYSTEM_PROMPT = """你是公众号爆款文章专家，深谙新媒体传播规律，写过大量10w+文章。
铁律：
1. 爆款 = 70%选题 + 20%标题 + 10%内容，选题永远第一位；选题决定80%成败
2. 爆款总公式：爆款 = 价值三支柱（利他·情绪·反差）× 表达六要素（强情绪/真细节/短节奏/好标题/强结构/高互动）；三支柱是骨架灵魂，六要素是血肉表达，缺一不可
3. 选题抓情绪：共鸣(扎心)/身份认同(说的就是我)/焦虑痛点/好奇悬念/利益相关
4. 标题五因素：话题(争议/反驳/好奇心)、热点(蹭流量)、痛点(共鸣歧义联想)、好奇(悬念留白)、利益(与我有关)；九宫格招式：数字、对比、悬念、身份、场景、反常、提问、承诺、热点
5. 开头黄金三秒（点开≠读完，前3秒决定去留）：反常识断言/扎心提问/场景代入/冲突前置/悬念预留/数据冲击/名人金句
6. 金句7大技法：①神转折(情理之中意料之外) ②押韵对仗(核心词+同音词) ③重复顶真(句尾重复/顶针) ④对比反差(反义词造句) ⑤反常语出惊人(打破常规+自圆其说) ⑥仿写流行语/名言诗词 ⑦比喻类比(具体化画面感)
7. 金句写作流程：提炼观点→精简句子→套用技法→反复打磨
8. 结构二选一：五段式(钩子开头→故事推进→观点金句→情绪升华→互动引导) 或 SCQA(情景→冲突→疑问→回答)
9. 结尾方法论：总结升华/金句收尾/互动引导(点赞在看评论转发)/留白余味，四选一或组合
10. 语言：口语化、短句(单句≤25字)、段落≤5行、有画面感、像朋友聊天不像写作文
11. 细节要求：真细节(具体数字/动作/对话/场景)，拒绝空话套话
12. 只输出中文结果，直接给干货，不要解释方法论
13. 微信搜一搜搜索流量铁律（官方《搜一搜优化教程01-04》+《快速入门》）：①标题必须清晰、简洁、直接，直给核心信息，让用户搜索词能命中；严禁标题党/夸大/文不对题——点开失望会被搜一搜降权，标题与正文强相关是底线 ②正文一篇一主题、鲜明详实可用、内容完整不藏，严禁「未完待续」「点击阅读原文」「长按识别加微信」等导流话术、隐藏文字作弊、欺骗下载 ③排版突出重点和层次（小标题/加粗/列表/留白），图片须可正常加载并配文字说明 ④优先声明原创，长期不更新/跨领域乱发会被排序打压
14. 爆款与搜索平衡：情绪钩子负责吸引点击，但内容必须兑现标题承诺，禁止「诱饵式标题」
15. 价值三支柱（文章能否爆的底层逻辑，动笔前先自检）：
    ① 利他性：读者看完必须带得走东西——方法/步骤/经验/避坑/认知/资源，能回答「对我有什么用？」；纯自嗨流水账=无利他=没人收藏转发
    ② 有情绪：内容必须让读者心里动一下——共鸣扎心/爽感/感动/愤怒/好奇/希望；情绪到位才有点赞评论收藏转发；干巴巴讲道理=无情绪=读完划走
    ③ 有反差：内容要有认知反转或冲突——「以为A，结果B」「别人都…他却…」「以前…现在…」；反差制造记忆点和传播欲；平铺直叙=无反差=没记忆点
    自检三问：读者能学到什么？会不会被打动？有没有反转？缺哪个补哪个，三者皆备才是能持续被推荐的文章"""


def _llm_ex(system_prompt: str, user_prompt: str, max_tokens: int = 2500,
             temperature: float = 0.9):
    """调用当前活跃 AI 模型（复用软件配置）。返回 (text, err)：
    text 不为 None 表示成功；失败时 text=None，err 为可读失败原因。"""
    try:
        from openai import OpenAI
        from src.config.loader import get_active_ai_config
        cfg = get_active_ai_config()
        key = cfg.get("api_key", "")
        url = cfg.get("base_url", "https://api.deepseek.com/v1")
        model = cfg.get("model", "")
        if not key:
            return None, "未配置 AI 模型 API Key（请到 设置→AI设置 配置）"
        if not model:
            return None, "未配置 AI 模型名称（请到 设置→AI设置 配置）"
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
        return resp.choices[0].message.content.strip(), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _llm(system_prompt: str, user_prompt: str, max_tokens: int = 2500,
         temperature: float = 0.9) -> str:
    """兼容旧调用：成功返回文本，失败返回 None（错误详情用 _llm_ex 获取）"""
    text, _ = _llm_ex(system_prompt, user_prompt, max_tokens, temperature)
    return text


def _llm_fail_text(err: str) -> str:
    """结构化失败标记：供 AI 大脑与 UI 层 100% 识别，附带可读原因"""
    _safe = (err or "未知错误").replace("\n", " ").replace("\r", " ")[:200]
    return f"⚠️ AI 深度生成失败：{_safe}\n[PLUGIN_ERROR] code=llm_failed msg={_safe}"


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
    if not keyword.strip():
        return "请提供主题/关键词，例如 viral_topic(keyword='中年人的体面')"
    prompt = (f"围绕「{keyword}」为目标人群「{audience}」生成 {count} 个公众号爆款选题。\n"
              f"选题要抓准3类流量密码：①强情绪(共鸣扎心/身份认同) ②实用刚需(利益相关/省钱避坑) ③好奇猎奇(悬念/反差/未解)。\n"
              f"每个选题输出格式：\n"
              f"[序号] 《选题标题雏形》\n"
              f"    情绪价值: 共鸣/身份认同/焦虑/好奇/利益（选其一，说明戳中什么）\n"
              f"    流量密码: 强情绪/实用刚需/好奇猎奇（标注属于哪类）\n"
              f"    目标人群: xxx\n"
              f"    爆款潜力: x.x/10（并一句话说明理由）\n"
              f"选题要覆盖不同情绪类型，避免同质化，优先选能引发争议和转发的角度。")
    text, _err = _llm_ex(SYSTEM_PROMPT, prompt, max_tokens=3500, temperature=1.0)
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
    return (_llm_fail_text(_err) + f"\n\n🔥 爆款选题 {count} 个（模板兜底）\n\n"
            + "\n".join(f"{i+1}. {t}" for i, t in enumerate(base))
            + "\n\n💡 提示：请检查 AI 模型配置后重试获取深度选题，或直接继续用 viral_title 生成标题。")


# ─────────────────── 2. 爆款标题 ───────────────────
@register_tool(
    name="viral_title",
    description="爆款标题生成：根据文章主题生成 10 个爆款标题，每个带类型标签（数字/悬念/身份/场景/对比/话题/热点/痛点/反常）和打开率预测。标题决定打开率，打开率决定推荐权重。",
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
    if not theme.strip():
        return "请提供文章主题，例如 viral_title(theme='中年人的体面和面子')"
    prompt = (f"根据主题「{theme}」生成 {count} 个公众号爆款标题。\n"
              f"要求：\n"
              f"1. 运用标题5大因素：话题(争议/反驳/好奇心)、热点(蹭流量)、痛点(共鸣/歧义联想)、好奇(悬念留白)、利益(与我有关)\n"
              f"2. 运用九宫格招式：数字具象、对比反差、悬念留白、身份代入、场景共鸣、反常语出惊人、扎心提问、承诺价值、热点借势\n"
              f"3. 覆盖不同类型：数字型/悬念型/身份型/场景型/对比型/话题型/痛点型至少各1个\n"
              f"4. 每个标题 ≤ 25 字，口语化，有情绪钩子，杜绝标题党欺骗\n"
              f"4.5 兼顾搜索流量（微信搜一搜官方规范）：标题必须清晰简洁直接、直给信息，尽量包含用户会搜索的核心关键词；点开后内容必须与标题强相关，禁止文不对题、夸张夸大\n"
              f"5. 输出格式：\n"
              f"[序号] 标题\n"
              f"    类型: 数字/悬念/身份/场景/对比/话题/痛点/热点/反常\n"
              f"    打开率预测: 高/中高/中 + 一句话说明为什么吸引人")
    text, _err = _llm_ex(SYSTEM_PROMPT, prompt, max_tokens=3000, temperature=1.0)
    if text:
        return f"✍️ 爆款标题 {count} 个\n\n{text}\n\n💡 建议：打开率预测最高的 3 个 A/B 测试，或选最贴合内容的一个。"
    # 兜底模板（9宫格招式全覆盖）
    bases = [
        ("数字", f"关于{theme}，我总结了 3 个真相"),
        ("悬念", f"{theme}？这是我听过最扎心的答案"),
        ("身份", f"40岁以后，才真正读懂{theme}"),
        ("场景", f"深夜一个人时，才明白{theme}的意义"),
        ("对比", f"越是{theme}的人，越不急着证明自己"),
        ("话题", f"别劝我{theme}，我不听"),
        ("痛点", f"那些为{theme}焦虑的人，都输给了自己"),
        ("反常", f"我劝你，别再{theme}了"),
        ("热点", f"最近大家都在聊{theme}，真相只有一个"),
    ]
    out = []
    for i in range(min(count, len(bases))):
        t, s = bases[i]
        out.append(f"{i+1}. {s}\n    类型: {t}\n    打开率预测: 中高")
    return _llm_fail_text(_err) + f"\n\n✍️ 爆款标题 {count} 个（模板兜底）\n\n" + "\n".join(out)


# ─────────────────── 3. 爆款大纲 ───────────────────
@register_tool(
    name="viral_outline",
    description="爆款大纲生成：根据选题生成爆款结构大纲，支持五段式（钩子开头→故事推进→观点金句→情绪升华→互动引导）或 SCQA（情景→冲突→疑问→回答），含每个小标题和写作要点。",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "选题/文章主题", "default": ""},
            "structure": {"type": "string", "description": "结构：五段式 / SCQA", "default": "五段式"},
        },
        "required": ["topic"],
    },
    category="viral",
)
def viral_outline(topic: str = "", structure: str = "五段式") -> str:
    """爆款大纲生成"""
    if not topic.strip():
        return "请提供选题，例如 viral_outline(topic='40岁才明白，人生最好的活法是这四个字')"
    if "SCQA" in structure.upper() or "scqa" in structure:
        prompt = (f"为选题「{topic}」生成 SCQA 结构爆款大纲。\n"
                  f"格式：\n"
                  f"📌 标题建议: （3个备选，运用九宫格招式）\n"
                  f"① S 情景(Situation): 描述读者熟悉的场景/背景，让人对号入座\n"
                  f"② C 冲突(Complication): 制造矛盾/痛点/转折，打破平衡\n"
                  f"③ Q 疑问(Question): 提出读者心中的问题，引发好奇\n"
                  f"④ A 回答(Answer): 给出观点/方案/故事，金句收尾\n"
                  f"⑤ 互动引导: 结尾如何引导点赞/在看/评论/转发")
    else:
        prompt = (f"为选题「{topic}」生成爆款五段式大纲。\n"
                  f"格式：\n"
                  f"📌 标题建议: （3个备选，运用九宫格招式）\n"
                  f"① 钩子开头(前3秒): 用哪种钩子（反常识/扎心提问/场景代入/冲突前置/悬念预留/数据冲击/名人金句）+示例开头\n"
                  f"② 故事推进: 小标题+讲什么故事+埋什么真细节（数字/对话/动作）\n"
                  f"③ 观点金句: 2-3个核心观点+对应金句（标注用了哪种金句技法）\n"
                  f"④ 情绪升华: 如何拔高到人生/价值层面，让人想转发\n"
                  f"⑤ 互动引导: 结尾如何引导点赞/在看/评论/转发")
    text, _err = _llm_ex(SYSTEM_PROMPT, prompt, max_tokens=2800, temperature=0.85)
    if text:
        return f"📐 爆款大纲：「{topic}」（{structure}）\n\n{text}\n\n💡 大纲确认后可继续用 viral_write 生成完整正文。"
    if "SCQA" in structure.upper():
        return (_llm_fail_text(_err) + f"\n\n📐 爆款大纲：「{topic}」（SCQA，模板兜底）\n\n"
                f"① S 情景：写出读者熟悉的日常场景，让人对号入座\n"
                f"② C 冲突：制造一个矛盾/痛点/转折，打破平静\n"
                f"③ Q 疑问：提出读者心里的问题，引发好奇\n"
                f"④ A 回答：给出观点+故事+方案，金句收尾\n"
                f"⑤ 互动：结尾提问/求点赞在看")
    return (_llm_fail_text(_err) + f"\n\n📐 爆款大纲：「{topic}」（模板兜底·标准五段式）\n\n"
            f"① 钩子开头：反常识/扎心提问/场景代入，3秒留住读者\n"
            f"② 故事推进：讲 1-2 个身边人的具体故事，有细节有画面\n"
            f"③ 观点金句：提炼 2-3 个观点，每个配一句金句\n"
            f"④ 情绪升华：从个人故事升到普遍人生感悟\n"
            f"⑤ 互动引导：结尾提问/求点赞在看，引导评论区留言")


# ─────────────────── 4. 爆款正文 ───────────────────
@register_tool(
    name="viral_write",
    description="爆款正文撰写：根据选题+大纲生成完整文章正文（公式驱动：强情绪+真细节+短节奏+好标题+强结构+高互动；黄金三秒开头+金句技法），可直接粘贴到公众号编辑器。",
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
    if not topic.strip():
        return "请提供选题，例如 viral_write(topic='40岁才明白，人生最好的活法是这四个字')"
    prompt = (f"根据选题「{topic}」写一篇 {word_count} 字左右的公众号爆款文章正文。\n"
              f"大纲参考（若有）：{outline[:1500] if outline else '自动按五段式结构'}\n"
              f"要求（爆款公式：强情绪+真细节+短节奏+好标题+强结构+高互动）：\n"
              f"1. 结构：五段式（钩子开头→故事推进→观点金句→情绪升华→互动引导）\n"
              f"2. 开头黄金三秒：前50字必须用钩子（反常识断言/扎心提问/场景代入/冲突前置/悬念预留/数据冲击/名人金句），绝不能平淡开场\n"
              f"3. 真细节：故事要有具体数字、动作、对话、场景，拒绝空话套话\n"
              f"4. 短节奏：单句 ≤25 字，段落 ≤5 行，多用短句和空行，读起来不累\n"
              f"5. 至少 3 个金句（用「」标出），每个金句必须运用7大技法之一（神转折/押韵对仗/重复顶真/对比反差/反常/仿写/比喻）\n"
              f"6. 有具体人物故事细节，不要空谈道理；写故事用「我朋友/同事/同学」增加真实感\n"
              f"7. 正文用 ## 作为小标题分隔，段落之间用空行\n"
              f"8. 结尾用四法之一或组合：总结升华/金句收尾/互动引导/留白余味，并引导点赞/在看/评论/转发\\n"
              f"9. 搜索流量（微信搜一搜官方规范）：一篇一主题写透不贪多；标题与正文强相关；正文内容完整可独立成文，严禁「未完待续/点击阅读原文/长按识别」等导流话术和隐藏文字；适当用小标题和加粗突出重点")
    text, _err = _llm_ex(SYSTEM_PROMPT, prompt, max_tokens=4000, temperature=0.95)
    if text:
        return f"📝 爆款正文：「{topic}」（约{word_count}字）\n\n{text}"
    return (_llm_fail_text(_err) + f"\n\n📝 爆款正文：「{topic}」（模板兜底，请修复 AI 配置后重试）\n\n"
            f"① 钩子：{topic}，这个问题的答案，藏在我两个朋友的故事里。\n\n"
            f"② 故事：发小的故事（细节+转折+感悟）……\n\n"
            f"③ 观点：**{topic}，才是成年人最大的清醒。**\n\n"
            f"④ 升华：人生没有白走的路，每一步都算数。\n\n"
            f"⑤ 互动：你身边有这样的故事吗？评论区聊聊。觉得有用，点个【在看】让更多人看到。")


# ─────────────────── 5. 金句卡片文案 ───────────────────
@register_tool(
    name="viral_quotes",
    description="金句卡片文案：从文章或主题中提取/生成 6 条金句（每条 20 字内，适合做成 1080x608 金句卡片配图），按7大技法生成，带排版建议和卡片标题。",
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
    if not article.strip():
        return "请提供文章内容或主题，例如 viral_quotes(article='40岁才明白，人生最好的活法是……')"
    prompt = (f"从以下文章/主题中提取并润色 6 条金句，每条 ≤ 20 字，适合做成金句卡片配图。\n"
              f"每条金句必须运用7大技法之一，并在标注里写明技法：\n"
              f"  ①神转折（情理之中意料之外）②押韵对仗 ③重复/顶真 ④对比反差 ⑤反常语出惊人 ⑥仿写流行语/名言 ⑦比喻类比\n"
              f"输出格式：\n"
              f"[1] 金句内容\n"
              f"    技法: 神转折/押韵/重复/对比/反常/仿写/比喻\n"
              f"    卡片标题: 2-4字（如：体面/清醒/活着）\n"
              f"    场景: 放文章开头/结尾/第几段后\n\n"
              f"文章：\n{article[:3000]}")
    text, _err = _llm_ex(SYSTEM_PROMPT, prompt, max_tokens=1800, temperature=0.9)
    if text:
        return f"💬 金句卡片文案 6 条\n\n{text}\n\n💡 可继续用配图工具把金句做成 1080x608 卡片插入文章。"
    return (_llm_fail_text(_err) + "\n\n💬 金句卡片文案 6 条（模板兜底）\n\n"
            "[1] 人生没有白走的路，每一步都算数。\n    技法: 仿写\n    卡片标题: 路\n    场景: 结尾\n"
            "[2] 真正成熟，是学会和自己和解。\n    技法: 反常\n    卡片标题: 和解\n    场景: 第2段后\n"
            "[3] 你羡慕的生活，都是别人熬出来的。\n    技法: 对比\n    卡片标题: 熬\n    场景: 第3段后\n"
            "[4] 最好的活法，是活成自己。\n    技法: 重复\n    卡片标题: 自己\n    场景: 开头\n"
            "[5] 慢慢来，比较快。\n    技法: 反常\n    卡片标题: 节奏\n    场景: 第4段后\n"
            "[6] 愿你起落有致，归来仍是少年。\n    技法: 押韵\n    卡片标题: 少年\n    场景: 结尾")


# ─────────────────── 6. 发布前检查 ───────────────────
@register_tool(
    name="viral_check",
    description="发布前质量检查：检查标题长度、正文长度、黄金三秒开头、结构完整性（钩子/故事/金句/互动）、段落节奏、敏感词风险，输出修改建议。发布前必用。",
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
    issues, ok = [], []

    # ── 标题检查 ──
    if title:
        n = len(title)
        if n > 64:
            issues.append(f"⚠️ 标题过长：{n} 字（公众号限 64 字）→ 建议精简到 25 字内")
        elif n > 25:
            ok.append(f"✅ 标题 {n} 字，未超限（建议 ≤25 字更抓眼）")
        else:
            ok.append(f"✅ 标题 {n} 字，长度合适")
        # 标题钩子元素检查（九宫格：数字/悬念/身份/场景/对比/话题/痛点/反常/热点）
        hooks = ["?", "？", "!", "！", ":", "：", "3", "5", "10", "40", "100",
                 "别", "劝", "真相", "秘密", "后悔", "戒", "最", "越", "才", "再"]
        if not any(k in title for k in hooks):
            issues.append("💡 标题缺少钩子元素（数字/悬念/对比/身份等），建议用 viral_title 优化")
        else:
            ok.append("✅ 标题含情绪钩子元素")
    else:
        issues.append("❌ 标题为空！")

    # ── 正文长度 ──
    text = content or ""
    n = len(text.replace("\n", "").replace(" ", ""))
    if n < 300:
        issues.append(f"❌ 正文过短：{n} 字（建议 ≥800 字，否则完读率和推荐权重低）")
    elif n < 800:
        issues.append(f"⚠️ 正文偏短：{n} 字（建议 1000-2000 字最佳）")
    else:
        ok.append(f"✅ 正文 {n} 字，长度适合")

    # ── 黄金三秒开头检查（前50字） ──
    if text:
        head = text[:60]
        head_hooks = ["？", "?", "!", "！", "你", "我", "昨天", "那天", "朋友", "同事", "发现",
                      "别再", "越", "最", "其实", "真相", "3", "10", "40", "100", "你们"]
        if not any(k in head for k in head_hooks):
            issues.append("💡 开头（前60字）缺少钩子：建议用反常识断言/扎心提问/场景代入/数字冲击开篇")
        else:
            ok.append("✅ 开头有钩子元素（黄金三秒）")

        # ── 段落节奏检查（长段落警告） ──
        paras = [p.strip() for p in text.split("\n") if p.strip()]
        long_paras = [len(p) for p in paras if len(p) > 150]
        if long_paras:
            issues.append(f"⚠️ 有 {len(long_paras)} 个段落超过150字，建议拆成 ≤5 行短段，提升完读率")
        else:
            ok.append("✅ 段落节奏良好（无超长段落）")

        # ── 结构检查 ──
        if not any(k in text for k in ["？", "?", "为什么", "怎么", "吗"]):
            issues.append("💡 正文缺少提问/悬念元素，开头钩子可加强")
        if "我" in text and ("朋友" in text or "同事" in text or "同学" in text or "发小" in text or "亲戚" in text):
            ok.append("✅ 有故事人物元素（增强代入感）")
        else:
            issues.append("💡 建议加入具体人物故事（朋友/同事/亲戚），增强代入感")
        if "点赞" in text or "在看" in text or "评论" in text or "留言" in text or "关注" in text or "转发" in text:
            ok.append("✅ 有互动引导")
        else:
            issues.append("💡 结尾缺少互动引导（点赞/在看/评论）")

        # ── 金句检查（「」数量） ──
        quote_cnt = len(re.findall(r"[「“\"](.+?)[」”\"]", text))
        if quote_cnt >= 3:
            ok.append(f"✅ 金句 {quote_cnt} 处（≥3 达标，可做金句卡片）")
        elif quote_cnt > 0:
            issues.append(f"💡 金句偏少：{quote_cnt} 处（建议 ≥3 处，用「」标出）")
        else:
            issues.append("💡 缺少金句（用「」标出至少3句，利于传播和做金句卡片）")

        # ── 真细节检查（数字/具体场景） ──
        if re.search(r"\d{1,3}(岁|年|天|块|万|点|次|个)", text):
            ok.append("✅ 有具体数字细节（增强真实感）")
        else:
            issues.append("💡 缺少具体数字细节（如 42岁/第11条/3000块），真细节=高共鸣")

        # ── 价值三支柱检查（利他性/有情绪/有反差） ──
        altru_keys = ["方法", "步骤", "教程", "避坑", "经验", "技巧", "怎么", "如何", "清单", "攻略", "建议", "秘密", "真相"]
        emotion_keys = ["真的", "居然", "没想到", "哭了", "感动", "心疼", "扎心", "难受", "爽", "气", "恨", "爱", "怕", "慌", "悔", "笑", "怒"]
        contrast_keys = ["以为", "结果", "没想到", "其实", "反而", "居然", "却", "以前", "现在", "曾经", "从没", "第一次", "终于", "直到", "差点"]
        if any(k in text for k in altru_keys):
            ok.append("✅ 有利他性（方法/经验/避坑类干货，读者带得走）")
        else:
            issues.append("💡 缺乏利他性：读者看完带不走东西，建议加入方法/步骤/经验/避坑等干货")
        if any(k in text for k in emotion_keys):
            ok.append("✅ 有情绪（共鸣/爽/感动/好奇等情绪词出现）")
        else:
            issues.append("💡 缺乏情绪：内容偏干巴，建议加入真实故事/细节/情绪词，让读者心里动一下")
        if any(k in text for k in contrast_keys):
            ok.append("✅ 有反差（以为…结果…等认知反转）")
        else:
            issues.append("💡 缺乏反差：建议加入认知反转（以为A结果B/别人都…他却…），制造记忆点")

    # ── 搜一搜搜索流量检查（微信官方《搜一搜优化教程01-04》+《快速入门》） ──
    soso_issues = []
    clickbait_words = ["震惊", "竟然", "万万没想到", "不转不是", "速看", "删前速看", "惊呆", "疯了", "吓哭", "绝了", "重磅", "紧急"]
    if title:
        hit_cb = [w for w in clickbait_words if w in title]
        if hit_cb:
            soso_issues.append(f"⚠️ 搜一搜风险：标题含标题党词 {hit_cb}（教程01：标题要清晰简洁直接，过度夸张=点击失望=搜索降权）")
        else:
            ok.append("✅ 标题无标题党词（搜一搜友好）")
        if not re.search(r"(指南|教程|方法|步骤|攻略|技巧|怎么办|是什么|如何|为什么|多少钱|哪家|推荐|排行|清单|标准|最新|\d)", title):
            soso_issues.append("💡 搜一搜建议：标题建议包含用户会搜索的核心词（如 教程/指南/怎么办/攻略/最新），提升搜索命中率")
    ban_patterns = ["未完待续", "阅读原文", "长按识别", "点击阅读", "防失联", "关注新号", "加微信", "加我好友", "扫码进群", "回复关键词领取", "转发到朋友圈才能看"]
    hit_ban = [w for w in ban_patterns if w in text]
    if hit_ban:
        soso_issues.append(f"❌ 搜一搜封禁风险：正文含导流/诱导话术 {hit_ban}（教程02：恶意导流是10大封禁因素之一）")
    else:
        ok.append("✅ 无导流/隐藏文字（合规）")
    if text.count("##") >= 6:
        soso_issues.append("💡 搜一搜建议：小标题过多可能主题分散，教程01要求一篇一主题写透")
    soso_issues.append("💡 搜一搜建议：发布时勾选「原创声明」+ 图片配文字说明（教程01：原创加权、图片可用）")
    issues += soso_issues

    # ── 敏感词快速预检（正式发布前仍会走系统敏感词审核） ──
    import re as _re
    risky = _re.findall(r"(政治|领导|政府|国家|共产党|台湾|独立|分裂|暴乱|恐怖|死亡|自杀|赌博|贷款|投资|炒股|稳赚|包治|百分百|最|第一|国家级|绝对|史上)", text + title)
    if risky:
        issues.append(f"⚠️ 命中疑似敏感/违规词：{'、'.join(set(risky))}（发布前需用系统审核确认）")
    else:
        ok.append("✅ 未检出常见敏感词")

    report = ["📋 发布前检查报告（v3.0 三支柱版：利他+情绪+反差 × 强情绪+真细节+短节奏+好标题+强结构+高互动）\n"]
    report += ok if ok else []
    report += issues if issues else ["🎉 全部检查通过！"]
    score = max(0, 100 - len(issues) * 10)
    report.append(f"\n📊 综合评分：{score}/100" + ("（建议修改后发布）" if issues else "（可以发布！）"))
    return "\n".join(report)


# ─────────────────── 7. 搜一搜搜索流量诊断 ───────────────────
@register_tool(
    name="viral_soso",
    description="搜一搜搜索流量诊断：根据微信官方《搜一搜优化教程01-04》+《快速入门》检查标题/正文/排版/原创/合规，输出搜索流量评分与修改建议。公众号文章发布前必用（搜索流量版viral_check）。",
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
def viral_soso(title: str = "", content: str = "") -> str:
    """搜一搜搜索流量诊断（本地规则，基于微信官方搜一搜优化教程01-04+快速入门）"""
    issues, ok = [], []
    text = content or ""

    # ── ① 标题：清晰简洁直接（教程01+快速入门Q1） ──
    if not title.strip():
        issues.append("❌ 标题为空！没有标题=没有搜索入口")
    else:
        n = len(title)
        if n > 30:
            issues.append(f"⚠️ 标题 {n} 字偏长（官方建议清晰简洁直接，≤25字最佳）")
        else:
            ok.append(f"✅ 标题 {n} 字，简洁达标")
        clickbait = ["震惊", "竟然", "万万没想到", "不转不是", "速看", "删前", "惊呆", "疯了", "吓哭", "重磅", "紧急"]
        hit = [w for w in clickbait if w in title]
        if hit:
            issues.append(f"❌ 标题党风险：{hit}（教程01：标题直给信息，过度夸张=点击失望=搜索降权）")
        else:
            ok.append("✅ 无标题党词")
        if not re.search(r"(指南|教程|方法|步骤|攻略|技巧|怎么办|是什么|如何|为什么|多少钱|哪家|推荐|排行|清单|标准|最新|\d)", title):
            issues.append("💡 标题信息不直给：建议加入用户会搜索的核心词（教程/指南/怎么办/攻略/数字），提升搜索命中")
        else:
            ok.append("✅ 标题直给信息（含核心词/数字）")

    # ── ② 正文：鲜明详实可用、完整不藏（教程01+02） ──
    n = len(text.replace("\n", "").replace(" ", ""))
    if n < 300:
        issues.append(f"❌ 正文过短 {n} 字（教程01：正文要详实，建议≥800字）")
    elif n < 800:
        issues.append(f"⚠️ 正文偏短 {n} 字（建议1000-2000字，内容充实才被搜一搜认可）")
    else:
        ok.append(f"✅ 正文 {n} 字，详实达标")
    ban = ["未完待续", "阅读原文", "长按识别", "点击阅读", "防失联", "关注新号", "加微信", "扫码进群", "回复关键词领取"]
    hit_ban = [w for w in ban if w in text]
    if hit_ban:
        issues.append(f"❌ 封禁风险：含导流/诱导话术 {hit_ban}（教程02：恶意导流是10大封禁因素）")
    else:
        ok.append("✅ 无导流/隐藏文字")
    if "##" in text:
        ok.append("✅ 有小标题分层（排版突出重点）")
    else:
        issues.append("💡 建议加小标题/加粗/列表突出重点（教程01：排版突出层次）")

    # ── ③ 原创与账号（教程01+快速入门Q4） ──
    issues.append("💡 发布时务必勾选「原创声明」（原创文章搜索加权）")

    report = ["🔍 搜一搜搜索流量诊断（官方教程01-04+快速入门）\n"]
    report += ok if ok else []
    report += issues if issues else ["🎉 全部达标！"]
    score = max(0, 100 - len(issues) * 12)
    report.append(f"\n📊 搜索流量评分：{score}/100" + ("（建议按上述修改后发布）" if issues else "（可以发布！）"))
    return "\n".join(report)
