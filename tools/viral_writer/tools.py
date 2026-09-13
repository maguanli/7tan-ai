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
2. 爆款总公式：爆款 = 价值四支柱（受众·利他·情绪·反差）× 表达六要素（强情绪/真细节/短节奏/好标题/强结构/高互动）；四支柱是骨架灵魂，六要素是血肉表达，缺一不可
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
15. 价值四支柱（文章能否爆的底层逻辑，动笔前先自检，受众永远第一位）：
    ① 受众：先明确这篇文章写给谁——年龄/身份/痛点/场景（如 30-45岁中年人、宝妈、打工人、家里有老人的子女）；受众越具体，选题越准、推荐越精准；「写给所有人=没人觉得与他有关」；动笔前先问：目标读者是谁？他在什么场景下会点开？会转发给谁？
    ② 利他性：读者看完必须带得走东西——方法/步骤/经验/避坑/认知/资源，能回答「对我有什么用？」；纯自嗨流水账=无利他=没人收藏转发
    ③ 有情绪：内容必须让读者心里动一下——共鸣扎心/爽感/感动/愤怒/好奇/希望；情绪到位才有点赞评论收藏转发；干巴巴讲道理=无情绪=读完划走
    ④ 有反差：内容要有认知反转或冲突——「以为A，结果B」「别人都…他却…」「以前…现在…」；反差制造记忆点和传播欲；平铺直叙=无反差=没记忆点
    自检四问：读者是谁？能学到什么？会不会被打动？有没有反转？缺哪个补哪个，四者皆备才是能持续被推荐的文章
16. 图文结构铁律（爆款排版核心，决定完读率和推荐权重，写正文必须标注配图）：
    ① 图片不少于6张：每篇爆款至少配6张图，图文穿插分布，严禁文末一次性堆图
    ② 每变一图：每个信息单元（一个变化/一个故事/一个观点/一个步骤）讲完就配一张图，图是段落之间的"呼吸节拍器"，制造"再来一段"的惯性
    ③ 用意象隐喻图：优先选无文字的意象图（钱/房/钥匙/城市/时钟/背影/路等抽象符号），拒绝人物摆拍照、大字报、数据截图——意象图不泄露情绪、让读者自动脑补自己的场景，代入感更强
    ④ 无文字图=不抢注意力：图扫一眼就过，眼睛立刻回到文字，完读率不掉
    ⑤ 图文比例≈1:1：一段文字配一张图，像刷短视频一样一屏一屏往下滑
    ⑥ 每张图配一句图注（文字说明），图文互相印证
    ⑦ 配图标准模板：钱袋子题材→硬币/钱包/算盘；房产题材→房子/钥匙/门；政策题材→文件/印章/城市天际线；情感题材→背影/牵手/灯光
17. 去AI痕迹铁律（发布前自查，AI腔=读者一眼出戏=完读率崩）：
    ① 禁空洞词：值得注意的是/众所周知/毋庸置疑/总而言之/综上所述/首先/其次/最后/值得一提的是/不难发现/由此可见/在这个快节奏的时代/让我们/值得我们深思——出现即重写
    ② 禁「不是A，是B」总结腔滥用：正文叙述里连续使用就是AI味，全篇最多3处且只留给标题/小标题/金句设计位；叙述中一律改成口语（怕的是/其实是/说白了）
    ③ 禁三连排比「是A，是B，是C」和「不是X，不是Y，是Z」句式
    ④ 禁感叹号滥用：每段≤1个，正文叙述尽量不用
    ⑤ 禁金句撞车：同一句式（如「怕的不是…是…」）全文不得重复出现两次
    ⑥ 口语优先：多用「其实/说白了/真要说起来/可/哪是什么」等口语连接词，像朋友聊天不像写作文；少用书面连接词（然而/此外/由此可见/综上）
    ⑦ 禁文艺腔套话：仿佛/宛如/恰似/岁月静好/流光溢彩等，一篇文章最多1处
    ⑧ 写完每段自问：这句话人会说吗？AI能批量生成的句子就重写
    ⑨ 禁「写在最后/结语/总结一下/最后说几句/写在结尾/写在文末」等总结陈词式小标题：结尾直接自然收束（抛问题/给建议/一句反问），禁止给自己贴「总结」标签，AI最爱这么结尾"""


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
        _msg = resp.choices[0].message
        _content = getattr(_msg, 'content', None)
        if not (_content or '').strip():
            _content = getattr(_msg, 'reasoning_content', None) or ''
        try:
            from pathlib import Path as _P
            (ROOT / 'tmp').mkdir(parents=True, exist_ok=True)
            (ROOT / 'tmp' / 'viral_llm_debug.log').open('a', encoding='utf-8').write(f"[OK] model={model} url={url} key_len={len(key)} content_len={len(_content) if _content else 0} content_type={type(_content).__name__}\n")
        except Exception:
            pass
        _text = (_content or '').strip()
        if not _text:
            return None, "模型返回了空内容（content 与 reasoning_content 均为空），请重试或切换模型"
        return _text, None
    except Exception as e:
        try:
            from pathlib import Path as _P
            (ROOT / 'tmp').mkdir(parents=True, exist_ok=True)
            (ROOT / 'tmp' / 'viral_llm_debug.log').open('a', encoding='utf-8').write(f"[ERR] model={model} url={url} key_len={len(key)} exc={type(e).__name__}: {e}\n")
        except Exception:
            pass
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

# ─── viral_write 输出清洗：过滤混入的"内部检查说明/要求复述"行（保守规则，避免误删正文） ───
_META_LEAD = ("注意", "提醒", "检查", "请确保", "务必", "我们设置", "我们要求", "写作要求", "输出要求", "提示：", "提示:")
_META_TERM = ("AI", "金句", "小标题", "图片", "字数", "结构", "敏感词", "搜索流量", "黄金三秒", "五段式", "去AI", "AI痕迹", "禁AI")


def _strip_viral_meta(text: str) -> str:
    """清洗 viral_write 输出中混入的'内部检查说明/要求复述'行（保守规则，避免误删正文）。"""
    if not text:
        return text
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            out.append(line)
            continue
        # 规则1：以自检动词开头 且 (以冒号结尾 或 含方法论术语) → 判定为混入的自检行
        if s.startswith(_META_LEAD):
            if s.rstrip("。！!，,").endswith(("：", ":")) or any(t in s for t in _META_TERM):
                continue
        # 规则2：≤40字的纯规则复述短行（以冒号/句号结尾且含强内部术语）
        if len(s) <= 40 and s.rstrip("。").endswith(("：", ":", "。")) and any(t in s for t in ("禁AI", "AI痕迹", "金句至少", "图片不少于", "去AI", "黄金三秒", "小标题分隔")):
            continue
        out.append(line)
    return "\n".join(out).strip()


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
                  f"⑤ 互动引导: 结尾如何引导点赞/在看/评论/转发\n"
                  f"⑥ 图文规划: 标注全文配图位置，不少于6张，每个故事/观点后配一张无文字意象图（钱/房/钥匙/城市/时钟/背影等），并用一句话注明图片内容建议")
    else:
        prompt = (f"为选题「{topic}」生成爆款五段式大纲。\n"
                  f"格式：\n"
                  f"📌 标题建议: （3个备选，运用九宫格招式）\n"
                  f"① 钩子开头(前3秒): 用哪种钩子（反常识/扎心提问/场景代入/冲突前置/悬念预留/数据冲击/名人金句）+示例开头\n"
                  f"② 故事推进: 小标题+讲什么故事+埋什么真细节（数字/对话/动作）\n"
                  f"③ 观点金句: 2-3个核心观点+对应金句（标注用了哪种金句技法）\n"
                  f"④ 情绪升华: 如何拔高到人生/价值层面，让人想转发\n"
                  f"⑤ 互动引导: 结尾如何引导点赞/在看/评论/转发\n"
                  f"⑥ 图文规划: 标注全文配图位置，不少于6张，每个故事/观点后配一张无文字意象图（钱/房/钥匙/城市/时钟/背影等），并用一句话注明图片内容建议")
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
              f"1. 去AI痕迹（最高优先级铁律，违反=废稿）：宁可平实朴素，不可有一丝AI腔；检测到AI痕迹直接判不合格重写。①禁空洞词（值得注意的是/众所周知/总而言之/综上所述/在这个快节奏的时代/让我们）②严禁连续用「不是A，是B」总结腔，全篇最多1处且只留标题/金句，叙述一律用口语（怕的是/其实是/说白了）③禁三连排比「是A，是B，是C」④每段感叹号≤1个⑤金句宁缺毋滥：全文最多1-2句且必须自然口语，禁止为凑金句堆排比对仗⑥口语优先像聊天，严禁书面连接词（然而/由此可见/综上/无疑/显然）⑦写完逐句自问「这句话人会说吗」，AI腔就重写⑧严禁「写在最后/结语/总结一下/最后说几句」等总结陈词式小标题，结尾直接自然收束不贴「总结」标签⑨结尾禁止强行升华拔高讲大道理，人话收尾即可\n"
              f"2. 结构：五段式（钩子开头→故事推进→观点金句→情绪升华→互动引导）\n"
              f"3. 开头黄金三秒：前50字必须用钩子（反常识断言/扎心提问/场景代入/冲突前置/悬念预留/数据冲击/名人金句），绝不能平淡开场\n"
              f"4. 真细节：故事要有具体数字、动作、对话、场景，拒绝空话套话\n"
              f"5. 短节奏：单句 ≤25 字，段落 ≤5 行，多用短句和空行，读起来不累\n"
              f"6. 金句（宁缺毋滥，服从第1条去AI铁律）：全文最多1-2处，必须自然口语，禁止堆排比对仗凑金句\n"
              f"7. 有具体人物故事细节，不要空谈道理；写故事用「我朋友/同事/同学」增加真实感\n"
              f"8. 正文用 ## 作为小标题分隔，段落之间用空行\n"
              f"9. 结尾用四法之一或组合：总结升华/金句收尾/互动引导/留白余味，并引导点赞/在看/评论/转发\\n"
              f"10. 搜索流量（微信搜一搜官方规范）：一篇一主题写透不贪多；标题与正文强相关；正文内容完整可独立成文，严禁「未完待续/点击阅读原文/长按识别」等导流话术和隐藏文字；适当用小标题和加粗突出重点\n"
              f"11. 图文结构（必做，爆款标配）：正文用【图片1】【图片2】…【图片N】单独成行标注插入位置，全文不少于6张图；每个故事/观点讲完配一张无文字意象图（钱/房/钥匙/城市/时钟/背影等），并在标记后注明图片内容建议（如【图片1】一堆硬币+微型小人，象征你的钱）；图文比例约1:1\n"
              
              f"\n12. 输出铁律（违反=废稿）：只输出文章正文本身，从第一个字起就是正文；严禁输出任何规则复述、检查清单、自检说明、写作提示、方法论文案；严禁出现「注意」「检查」「提醒」「请确保」「我们设置」「记得」「要求」「说明」等自检字眼开头的句子；严禁以「以下是正文」「开始写作」「写作要点」等话术开头或结尾；不要解释你将如何写，直接写。{word_count} 字只统计正文，不统计任何标注。")
    text, _err = _llm_ex(SYSTEM_PROMPT, prompt, max_tokens=6000, temperature=0.95)
    if text:
        text = _strip_viral_meta(text)
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


# ─────────────────── 6.0 AI风格软痕迹检测（移植自 novel_writer 6类检测，按公众号文体适配） ───────────────────
AI_POINT_WORDS_VIRAL = ["原来", "其实", "也就是说", "说白了", "换句话说", "这意味着",
                        "说白了就是", "说穿了", "归根结底"]


def _viral_ai_style_hits(text):
    """检测6类AI写作软痕迹（移植自 novel_writer._ai_style_hits，按公众号文体适配）。"""
    hits = []
    paras = [p.strip() for p in text.split("\n") if p.strip()]

    # 1. 金句点题独立成段：短句(≤15字)以点题连接词开头，独立成段下结论
    point_lead = ["原来", "其实", "所以", "因为", "只是", "不过", "说到底", "说白了",
                  "换句话说", "这意味着", "这才是", "原来如此", "归根结底", "也许", "或许"]
    aphorism = [p for p in paras if 2 < len(p) <= 15 and p[0] not in ("「", "“", "【")
                and any(p.startswith(w) for w in point_lead)]
    if len(aphorism) >= 4:
        hits.append("⚠️ 金句点题×{}（点题词开头的短句独立成段过多，AI总结腔；公众号金句段可保留，但点题词开头需减少）".format(len(aphorism)))

    # 2. 破折号悬置：—— 出现过多，或句尾悬置（话说一半吊胃口）
    dash = text.count("——")
    dash_suspend = len(re.findall(r"[^。！？\n]{0,12}——\s*$", text, re.M))
    if dash >= 4 or dash_suspend >= 3:
        hits.append("⚠️ 破折号悬置×{}（话说一半吊胃口，全文建议≤2次）".format(dash))

    # 3. 三段式排比：同一段内 3 个以上相同骨架词（是/能说/不是/会/像）连接的短句
    for p in paras:
        if len(p) > 20 and len(re.findall(r"(?:是|能说|不是|会|像)[^，。！？]{0,14}[，。]", p)) >= 4:
            hits.append("⚠️ 三段式排比（工整排比句式，建议打散成口语）")
            break

    # 4. 直白点题：作者解释标记词过多（作者跳出来下结论）
    point_hits = [w for w in AI_POINT_WORDS_VIRAL if w in text]
    if len(point_hits) >= 3:
        hits.append("⚠️ 直白点题×{}（{}，作者跳出来下结论，建议让读者自己品）".format(len(point_hits), ",".join(point_hits[:3])))

    # 5. 台词工具人：单段引号内≥60字，一口气说完像在递证据
    long_quotes = re.findall(r"[“]([^”]{60,})[”]", text)
    if long_quotes:
        hits.append("⚠️ 台词过长×{}（单段≥60字像在递证据，建议拆成口语短句）".format(len(long_quotes)))

    # 6. 「我」主语重复：公众号第一人称是常态，仅当段首「我」极度单一(≥18段)才提示
    wo_paras = [p for p in paras if p.startswith("我") and len(p) >= 6]
    if len(wo_paras) >= 18:
        hits.append("⚠️ 「我」开头段落×{}（第一人称极度单一，建议穿插场景/他人视角）".format(len(wo_paras)))

    return hits


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

        # ── 图片数量检查（爆款图文结构：≥6张） ──
        img_cnt = len(re.findall(r"【图片\d+】", text))
        if img_cnt >= 6:
            ok.append(f"✅ 配图标记 {img_cnt} 处（≥6 达标，图文节奏符合爆款标准）")
        elif img_cnt > 0:
            issues.append(f"⚠️ 配图标记偏少：{img_cnt} 处（建议 ≥6 张，图文比例约1:1，每讲完一个故事/观点配一张图）")
        else:
            issues.append("💡 缺少配图标记：建议正文用【图片1】…【图片N】标注插入位置，全文不少于6张图（爆款图文结构铁律）")

        # ── AI痕迹检查（去AI腔，发布前自查） ──
        ai_issues = []
        empty_words = ["值得注意的是", "众所周知", "毋庸置疑", "总而言之", "综上所述", "首先", "其次", "值得一提", "不难发现", "由此可见", "在这个快节奏的时代", "让我们", "值得我们深思", "仿佛", "宛如"]
        hit_empty = [w for w in empty_words if w in text]
        if hit_empty:
            ai_issues.append(f"⚠️ AI空洞词 {hit_empty}（出现即改口语：说白了/其实/真要说起来）")
        notA_isB = len(re.findall(r"不是[^，。；、]{1,12}，[^，。；]{0,8}是[^，。；]{1,14}", text))
        if notA_isB > 3:
            ai_issues.append(f"⚠️ 「不是A，是B」句式 {notA_isB} 处（>3处=AI总结腔，叙述改口语：怕的是/其实是/说白了）")
        summary_titles = ["写在最后", "写在结尾", "写在文末", "结语", "总结一下", "最后说几句", "最后说句", "写在后面"]
        hit_sum = [w for w in summary_titles if w in text]
        if hit_sum:
            ai_issues.append(f"⚠️ 总结陈词式标题 {hit_sum}（「写在最后/结语」=AI痕迹，结尾改为自然收束：抛问题/给建议/一句反问）")
        bang_cnt = text.count("！")
        if bang_cnt > 5:
            ai_issues.append(f"⚠️ 感叹号过多：{bang_cnt} 个（每段≤1个，正文叙述尽量不用）")
        triple_cnt = len(re.findall(r"[，,][^，。；]{1,12}[，,][^，。；]{1,12}[，,][^，。；]{1,12}[。！？]", text))
        if triple_cnt >= 2:
            ai_issues.append(f"⚠️ 疑似三连排比 {triple_cnt} 处（是A，是B，是C=AI腔，建议拆短句口语化）")
        ai_issues += _viral_ai_style_hits(text)
        if ai_issues:
            issues += ai_issues
        else:
            ok.append("✅ AI痕迹检查通过（无空洞词/句式滥用）")

        # ── 价值四支柱检查（受众/利他性/有情绪/有反差） ──
        # ── 受众检查（写给谁：受众越具体，算法推荐越精准，支柱①） ──
        audience_keys = ["爸妈", "父母", "老人", "孩子", "子女", "家长", "宝妈", "打工人", "职场", "年轻人", "中年人", "学生", "毕业生", "求职", "买房", "还贷", "车主", "司机", "退休", "教师", "医生"]
        if any(k in text for k in audience_keys):
            ok.append("✅ 受众指向明确（开头/正文点出了目标人群）")
        else:
            issues.append("💡 缺乏明确受众：建议开头点明'写给谁看'（如：家里有老人的/还在还房贷的/带娃的妈妈…），受众清晰=算法推荐更精准")

        # ── 利他/情绪/反差检查（原三支柱） ──
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

    report = ["📋 发布前检查报告（v3.1 四支柱版：受众+利他+情绪+反差 × 强情绪+真细节+短节奏+好标题+强结构+高互动）\n"]
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
