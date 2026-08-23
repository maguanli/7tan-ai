"""
小说写作插件（番茄方向）— 模块⑤：质检引擎
按《番茄官方写作方法论手册》实现章节/全书质量扫描。
"""
import re
import os
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

# ============ 规则库 ============
STANDARD_CHARS = 2000
WARN_CHARS = 1800

BODY_REACTION_TEMPLATES = [
    "深吸一口气", "倒吸一口凉气", "倒吸一口冷气", "心头一沉", "心头一紧",
    "心头一跳", "心里咯噔", "咯噔一下", "浑身一震", "头皮发麻", "后背发凉",
    "背后发凉", "汗毛倒竖", "鸡皮疙瘩", "瞳孔骤缩", "瞳孔一缩", "瞳孔猛缩",
    "心里一紧", "嘴角勾起一抹", "眼中闪过一丝", "眼底闪过一丝",
]
SLOW_PACING_WORDS = [
    "缓缓", "默默", "良久", "久久", "静默", "沉默片刻", "沉默良久",
    "若有所思", "意味深长", "静静地看着", "静静站着", "轻轻点了点头",
]
EMPTY_ELEVATION_WORDS = [
    "宿命", "命运的安排", "命运的齿轮", "注定的", "这就是命", "灵魂深处",
    "生命的真谛", "人生的意义", "不忘初心", "内心深处的",
]
METAPHOR_PATTERNS = [
    r"像[^。！？\n]{0,12}(一样|一般|似的)",
    r"如同[^。！？\n]{0,12}(一般|一样)",
    r"仿佛[^。！？\n]{0,12}(一般|一样)",
    r"好像[^。！？\n]{0,10}(一样|似的)",
]
DIALOG_TAG_RICH = ["喊", "吼", "嚷", "嘟囔", "嘀咕", "喃喃", "冷哼", "嗤笑",
                   "接话", "插嘴", "应声", "咬牙", "压低声音", "扯着嗓子",
                   "反问", "追问", "打断", "附和", "劝", "吼回去", "阴阳怪气"]
SENSITIVE_BASIC = [
    "杀人放火", "强奸", "自杀", "枪支", "毒品", "贩毒", "血腥", "分尸",
    "轮奸", "卖淫", "赌博", "诈骗", "传销", "邪教", "法轮", "台独", "藏独",
]
MAX_PARAGRAPH_CHARS = 120
CHAPTER_END_MARK = re.compile(r"^第[一二三四五六七八九十百0-9]+章·完\s*$")
CN_QUOTE_LEFT = "\u201c"
CN_QUOTE_RIGHT = "\u201d"


def _clean_chapter(text):
    lines = text.split("\n")
    out = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if re.match(r"^《.*》$", s):
            continue
        if re.match(r"^第[一二三四五六七八九十百0-9]+章", s):
            continue
        if CHAPTER_END_MARK.match(s):
            continue
        out.append(s)
    return "\n".join(out)


def _count_chars(text):
    return len(re.sub(r"\s", "", text))


def _extract_dialog(text):
    dialogs = re.findall(r"[“\"]([^”\"]{1,200})[”\"]", text)
    dialog_chars = sum(len(d) for d in dialogs)
    return dialogs, dialog_chars


def _word_hits(text, words):
    return [(w, text.count(w)) for w in words if text.count(w) > 0]


def _hook_check(text):
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    if not paras:
        return False, "无内容"
    last = paras[-1]
    markers = ["？", "!", "！", "竟然", "没想到", "突然", "忽然", "就在这时",
               "完蛋", "糟了", "不对劲", "来了", "露出", "浮现", "响起",
               "怎么回事", "到底", "究竟是什么", "……", "…", "转机", "秘密",
               "真相", "不是", "难道", "莫非", "却", "竟", "——", "收编",
               "杀", "死", "任务", "系统", "门", "他", "她", "它"]
    score = sum(1 for m in markers if m in last)
    if len(last) <= 25 and ("“" in last or "”" in last):
        score += 3
    elif len(last) <= 25:
        score += 2
    elif len(last) <= 40:
        score += 1
    return score >= 2, last[:60]


def _quote_check(text):
    problems = []
    lc = text.count(CN_QUOTE_LEFT)
    rc = text.count(CN_QUOTE_RIGHT)
    if lc != rc:
        problems.append(f"中文引号未成对：左{lc} 右{rc}")
    straight = re.findall(r'"[^"\n]{1,60}"', text)
    if straight:
        problems.append(f"检测到{len(straight)}处英文直引号（番茄规范用中文引号“”，发布前建议统一替换）")
    single = re.findall(r"'[^'\n]{1,40}'", text)
    if single:
        problems.append(f"检测到{len(single)}处英文单引号（番茄规范用中文引号或「」）")
    return problems


# ============ 6类AI写作软痕迹检测（补充硬痕迹检测盲区） ============
# 硬痕迹（身体反应模板/节奏拖沓/空洞升华/比喻堆砌）查不出"软痕迹"，
# 以下 6 类由实际改稿经验归纳，逐条可程序化判定，以不误报为原则。

AI_POINT_WORDS = ["原来", "其实", "也就是说", "说白了", "换句话说", "这意味着",
                  "说白了就是", "说穿了", "归根结底"]


def _ai_style_hits(body):
    """检测6类AI写作软痕迹，返回提示列表（每条格式同 ai_hits）"""
    hits = []
    paras = [p.strip() for p in body.split("\n") if p.strip()]

    # 1. 金句点题独立成段：短句(≤15字)以段首总结/点题连接词开头，独立成段下结论
    point_lead = ["原来", "其实", "所以", "因为", "只是", "不过", "说到底", "说白了",
                  "换句话说", "这意味着", "这才是", "原来如此", "归根结底", "也许", "或许"]
    aphorism = [p for p in paras if 2 < len(p) <= 15 and p[0] not in ("「", "“", "【")
                and any(p.startswith(w) for w in point_lead)]
    if len(aphorism) >= 3:
        hits.append(f"金句点题×{len(aphorism)}（短句独立成段下结论过多，建议融入叙述）")

    # 2. 破折号悬置：—— 出现过多，或句尾悬置（话说一半吊胃口）
    dash = body.count("——")
    dash_suspend = len(re.findall(r"[^。！？\n]{0,12}——\s*$", body, re.M))
    if dash >= 4 or dash_suspend >= 3:
        hits.append(f"破折号悬置×{dash}（话说一半吊胃口，全章建议≤2次）")

    # 3. 三段式排比：同一段内 3 个以上相同骨架词（是/能说/不是/会/像）连接的短句
    for p in paras:
        if len(p) > 20 and len(re.findall(r"(?:是|能说|不是|会|像)[^，。！？]{0,14}[，。]", p)) >= 4:
            hits.append("三段式排比（工整排比句式，建议打散成口语）")
            break

    # 4. 直白点题：作者解释标记词过多（作者跳出来下结论）
    point_hits = [w for w in AI_POINT_WORDS if w in body]
    if len(point_hits) >= 3:
        hits.append(f"直白点题×{len(point_hits)}（{','.join(point_hits[:3])}，作者跳出来下结论，建议让读者自己品）")

    # 5. 台词工具人：单段引号内≥60字，一口气说完像在递证据
    long_quotes = re.findall(r"[“]([^”]{60,})[”]", body)
    if long_quotes:
        hits.append(f"台词过长×{len(long_quotes)}（单段≥60字像在递证据，建议拆成口语短句）")

    # 6. 「我」主语重复：段首"我"开头段落过多（第一人称流水账）
    wo_paras = [p for p in paras if p.startswith("我") and len(p) >= 6]
    if len(wo_paras) >= 12:
        hits.append(f"「我」开头段落×{len(wo_paras)}（第一人称主语重复，建议合并/换主语）")

    return hits


# ============ 6. 一致性检查（前后用词统一，模块⑤增强） ============

# 关键实体：用于'疑似变体'检测（仅 3-4 字实体，2字误报率高）
CONSISTENCY_ENTITIES = [
    '王二毛', '李大妈', '王桂芬', '无面者', '陈建国', '命运硬币', '试炼之塔',
    '塔心', '清除协议', '七枚碎片',
]

# 实体别名白名单：合法变体（人物昵称/物品简称等），不报警
ENTITY_ALIAS_WHITELIST = {
    '王二毛': ['黄毛', '二毛'],
    '李大妈': ['大妈', '李婶', '婶子'],
    '王桂芬': ['王婶', '桂芬'],
    '无面者': ['无面', '无面者公会'],
    '陈建国': ['父亲', '老爸', '爸爸', '老陈'],
    '命运硬币': ['硬币', '实体硬币', '那枚硬币', '命运'],
    '试炼之塔': ['塔', '高塔'],
    '塔心': ['塔心日志'],
    '清除协议': ['协议'],
}

# 场景关键词组：同组词在同一章内出现>=2个不同词 → 疑似用词不统一（如拆楼/烧楼）
# 场景关键词组（只收录'同一事件/动作的近似写法'，避免把不同概念误判为冲突）
SCENE_KEYWORD_GROUPS = {
    '烧楼威胁': ['烧楼', '拆楼', '放火烧', '点火'],
    '活捉方式': ['活捉', '活抓', '生擒', '抓活的'],
    '复制体': ['复制体', '克隆体', '复制人'],
    '实体硬币': ['实体硬币', '实物硬币'],
}

# 疑似变体误报忽略表（常见词）
VARIANT_IGNORE_WORDS = {
    '沉默', '考虑', '沉着', '安排', '情况', '心情', '事情', '热情',
    '成就', '成绩', '沉重', '成默',
}


def _text_windows(text, length):
    """真正的滑动窗口：每 length 个连续汉字为一窗（避免非重叠截断伪影）"""
    chars = re.findall(r'[\u4e00-\u9fff]', text)
    if len(chars) < length:
        return []
    return [''.join(chars[i:i + length]) for i in range(len(chars) - length + 1)]


def check_entity_variants(chapters):
    """检测实体疑似错误变体：仅 3-4 字实体，同长度仅一字不同、不在白名单/忽略表；
    候选词出现>=2次才提示（过滤单次窗口伪影）"""
    from collections import Counter
    all_text = ''.join(t for _, t in chapters)
    cnt = Counter()
    cand = {}
    for ent in CONSISTENCY_ENTITIES:
        if len(ent) < 3 or len(ent) > 4:
            continue
        whitelist = set(ENTITY_ALIAS_WHITELIST.get(ent, []))
        for w in _text_windows(all_text, len(ent)):
            if w == ent or w in whitelist or w in VARIANT_IGNORE_WORDS:
                continue
            diff = sum(1 for a, b in zip(w, ent) if a != b)
            if diff == 1:
                cnt[w] += 1
                cand.setdefault(w, ent)
    out = [(cand[w], w, c) for w, c in cnt.items() if c >= 2]
    out.sort(key=lambda x: -x[2])
    return out


def check_scene_keywords(chapters):
    """场景关键词一致性：
       per_chapter: 同章内同组出现多个不同词（强提示）
       global_dist: 同组词在全书的章节分布（跨章写法不统一提示）"""
    from collections import defaultdict
    per_chapter = []
    global_dist = defaultdict(dict)
    for title, text in chapters:
        for gname, words in SCENE_KEYWORD_GROUPS.items():
            hits = [(w, text.count(w)) for w in words if text.count(w) > 0]
            # 过滤包含关系：'清除' 是 '清除协议' 的子串，不算独立命中
            hits = [(w, c) for w, c in hits if not any(w in w2 and w != w2 for w2, _ in hits)]
            for w, c in hits:
                global_dist[gname][w] = global_dist[gname].get(w, []) + [title]
            if len(hits) >= 2:
                per_chapter.append((title, gname, hits))
    global_out = []
    for gname, wmap in global_dist.items():
        if len(wmap) >= 2:
            global_out.append((gname, wmap))
    return per_chapter, global_out


def check_duplicate_sentences(chapters, min_len=8):
    """跨章/章内完全重复句子（改稿残留/复制粘贴）"""
    from collections import Counter
    counter = Counter()
    loc = {}
    for title, text in chapters:
        for s in re.split(r'[。！？!?…]+', text):
            s2 = re.sub(r'[\s“”\'，,：:；;、（）()【】]+', '', s)
            if len(s2) >= min_len:
                counter[s2] += 1
                loc.setdefault(s2, []).append(title)
    return [(s, c, loc[s]) for s, c in counter.items() if c >= 2]


def check_time_numbers(chapters):
    """时间线/数量复核：列出所有 数字+单位；并检测倒计时数值反弹"""
    notes = []
    pat = re.compile(r'(\d+)(天|小时|分钟|秒|枚|个|点|年|章|次|人|层|米|元|%|％)')
    for title, text in chapters:
        for m in pat.finditer(text):
            start = max(0, m.start() - 10)
            ctx = text[start:m.end() + 10].replace('\n', ' ')
            notes.append((title, m.group(0), ctx))
    countdown = []
    for title, text in chapters:
        for m in re.finditer(r'(倒计时|还剩|剩余|只剩|还剩下|只剩下)[^。！？\n]{0,12}?(\d+)(天|小时|分钟)', text):
            countdown.append((title, m.group(0)))
    # 倒计时递减检查：同单位数字按章节顺序应单调递减，反弹则提示
    prev = {}
    countdown_warn = []
    for title, s in countdown:
        m = re.search(r'(\d+)(天|小时|分钟)', s)
        if not m:
            continue
        num, unit = int(m.group(1)), m.group(2)
        if unit in prev and num > prev[unit][1]:
            countdown_warn.append((title, s, prev[unit][0]))
        prev[unit] = (title, num)
    return notes, countdown, countdown_warn


def run_consistency_check(chapters):
    """全书一致性检查汇总"""
    per_chapter, global_dist = check_scene_keywords(chapters)
    notes, countdown, countdown_warn = check_time_numbers(chapters)
    return {
        'entity_variants': check_entity_variants(chapters),
        'scene_conflicts': per_chapter,
        'scene_global': global_dist,
        'duplicates': check_duplicate_sentences(chapters),
        'numbers': notes,
        'countdown': countdown,
        'countdown_warn': countdown_warn,
    }


def render_consistency(cons):
    """渲染一致性检查结果为 Markdown 行"""
    lines = ['', '## 五、前后用词一致性检查', '']
    if not cons:
        lines.append('- 未执行')
        return lines
    # 5.1 场景用词
    lines.append('### 5.1 场景用词统一性')
    sc = cons.get('scene_conflicts', [])
    if sc:
        for t, g, h in sc:
            words = '、'.join('「%s」×%d' % (w, c) for w, c in h)
            lines.append('- 🔴 %s｜组[%s]：%s → 同一章内用词不统一，请人工确认（如拆楼/烧楼）' % (t, g, words))
    else:
        lines.append('- ✅ 未发现同章场景用词冲突')
    sg = cons.get('scene_global', [])
    for gname, wmap in sg:
        parts = []
        for w, titles in wmap.items():
            parts.append('「%s」%d章(%s)' % (w, len(titles), ','.join(titles[:6])))
        lines.append('- ⚠️ 全书组[%s]出现多个近似词：%s → 若为同一事件/场景，建议统一' % (gname, '；'.join(parts)))
    # 5.2 实体变体
    lines.append('')
    lines.append('### 5.2 实体疑似变体（仅一字不同，需人工确认）')
    ev = cons.get('entity_variants', [])
    if ev:
        for item in ev:
            if len(item) == 3:
                e, w, c = item
                lines.append('- ⚠️ 实体「%s」疑似出现变体「%s」×%d（请确认是否为笔误）' % (e, w, c))
            else:
                e, w = item
                lines.append('- ⚠️ 实体「%s」疑似出现变体「%s」（请确认是否为笔误）' % (e, w))
    else:
        lines.append('- ✅ 未发现实体疑似变体')
    # 5.3 重复句
    lines.append('')
    lines.append('### 5.3 重复句子（改稿残留/复制粘贴）')
    dup = cons.get('duplicates', [])
    if dup:
        for s, c, loc in dup:
            lines.append('- ⚠️ 「%s」×%d（%s）' % (s, c, ', '.join(loc)))
    else:
        lines.append('- ✅ 未发现重复句子')
    # 5.4 时间线
    lines.append('')
    lines.append('### 5.4 时间/数量复核清单（供人工查矛盾）')
    nums = cons.get('numbers', [])
    countdown = cons.get('countdown', [])
    cw = cons.get('countdown_warn', [])
    if cw:
        lines.append('**⚠️ 倒计时数值反弹（疑似矛盾）：**')
        for t, s, p in cw:
            lines.append('- %s：%s（此前 %s 已出现更小值）' % (t, s, p))
    if countdown:
        lines.append('**倒计时记录（检查是否递减合理）：**')
        for t, s in countdown:
            lines.append('- %s：%s' % (t, s))
    if nums:
        shown = nums[:60]
        lines.append('**全书记录 %d 处数字（前 %d 条）：**' % (len(nums), len(shown)))
        for t, num, ctx in shown:
            lines.append('- %s｜%s｜…%s…' % (t, num, ctx))
    else:
        lines.append('- 未发现数字记录')
    return lines
    lines.append('### 5.1 场景用词统一性（同章出现同组近似词）')
    sc = cons.get('scene_conflicts', [])
    if sc:
        for t, g, h in sc:
            words = '、'.join('「%s」×%d' % (w, c) for w, c in h)
            lines.append('- ⚠️ %s｜组[%s]：%s → 疑似同一场景用词不统一，请人工确认' % (t, g, words))
    else:
        lines.append('- ✅ 未发现同章场景用词冲突')
    lines.append('')
    lines.append('### 5.2 实体疑似变体（仅一字不同，需人工确认）')
    ev = cons.get('entity_variants', [])
    if ev:
        for e, w in ev:
            lines.append('- ⚠️ 实体「%s」疑似出现变体「%s」（请确认是否为笔误）' % (e, w))
    else:
        lines.append('- ✅ 未发现实体疑似变体')
    lines.append('')
    lines.append('### 5.3 重复句子（改稿残留/复制粘贴）')
    dup = cons.get('duplicates', [])
    if dup:
        for s, c, loc in dup:
            lines.append('- ⚠️ 「%s」×%d（%s）' % (s, c, ', '.join(loc)))
    else:
        lines.append('- ✅ 未发现重复句子')
    lines.append('')
    lines.append('### 5.4 时间/数量复核清单（供人工查矛盾）')
    nums, countdown = cons.get('numbers', ([], []))
    if countdown:
        lines.append('**倒计时记录（检查是否递减合理）：**')
        for t, s in countdown:
            lines.append('- %s：%s' % (t, s))
    if nums:
        shown = nums[:60]
        lines.append('**全书记录 %d 处数字（前 %d 条）：**' % (len(nums), len(shown)))
        for t, num, ctx in shown:
            lines.append('- %s｜%s｜…%s…' % (t, num, ctx))
    else:
        lines.append('- 未发现数字记录')
    return lines



def _scan_chapter(title, text, is_chapter_one=False):
    problems = []
    stats = {}
    body = _clean_chapter(text)
    total = _count_chars(body)
    stats["chars"] = total

    if total < STANDARD_CHARS:
        problems.append({
            "level": "WARN" if total >= WARN_CHARS else "ERROR",
            "rule": "章节长度",
            "msg": f"共{total}字符，不足标准{STANDARD_CHARS}（短章影响完读率/推荐）"
        })

    ai_hits = []
    for w, c in _word_hits(body, BODY_REACTION_TEMPLATES):
        ai_hits.append(f"身体反应模板「{w}」×{c}")
    for w, c in _word_hits(body, SLOW_PACING_WORDS):
        ai_hits.append(f"节奏拖沓词「{w}」×{c}")
    for w, c in _word_hits(body, EMPTY_ELEVATION_WORDS):
        ai_hits.append(f"空洞升华「{w}」×{c}")
    for p in METAPHOR_PATTERNS:
        ms = re.findall(p, body)
        if ms:
            ai_hits.append(f"比喻堆砌「{ms[0]}」×{len(ms)}")
    for h in _ai_style_hits(body):
        ai_hits.append(h)
    stats["ai_hits"] = ai_hits
    if ai_hits:
        problems.append({"level": "WARN", "rule": "AI痕迹", "msg": "; ".join(ai_hits[:10])})

    dialogs, dchars = _extract_dialog(body)
    ratio = dchars / total if total else 0
    stats["dialog_ratio"] = round(ratio, 3)
    if ratio < 0.25:
        problems.append({"level": "INFO", "rule": "对话比例",
                         "msg": f"对话占比仅{ratio:.0%}（爆款对话流通常50%+；系统流/设定章可偏低）"})
    tag_hits = sum(body.count(t) for t in DIALOG_TAG_RICH)
    plain_say = len(re.findall(r"说[:：]", body)) + len(re.findall(r"说道", body))
    stats["say_count"] = plain_say
    stats["rich_tag_count"] = tag_hits
    if plain_say > 12 and tag_hits < 3:
        problems.append({"level": "INFO", "rule": "对话标签",
                         "msg": f"「说」{plain_say}次而丰富标签仅{tag_hits}种，可穿插喊/吼/嘟囔/冷哼等"})

    paras = [p.strip() for p in body.split("\n") if p.strip()]
    long_paras = [p for p in paras if len(p) > MAX_PARAGRAPH_CHARS]
    stats["long_paras"] = len(long_paras)
    if long_paras:
        problems.append({"level": "INFO", "rule": "段落节奏",
                         "msg": f"{len(long_paras)}个超长段落(>{MAX_PARAGRAPH_CHARS}字)，建议拆行"})

    boxes = len(re.findall(r"【[^】]{1,80}】", body))
    stats["system_boxes"] = boxes
    box_chars = sum(len(m) for m in re.findall(r"【[^】]{1,80}】", body))
    box_ratio = box_chars / total if total else 0
    stats["box_ratio"] = round(box_ratio, 3)
    threshold = 0.18 if is_chapter_one else 0.10
    if boxes > 6 and box_ratio > threshold:
        problems.append({"level": "WARN", "rule": "系统面板",
                         "msg": f"【】面板{boxes}个、占正文{box_ratio:.0%}，超{threshold:.0%}阈值（面板过多=水字数）"})

    hooked, preview = _hook_check(body)
    stats["hook"] = hooked
    stats["last_preview"] = preview
    if not hooked:
        problems.append({"level": "ERROR", "rule": "章末钩子",
                         "msg": f"章末缺乏悬念钩子（一章写80%，留20%给下一章）。末段：{preview}"})

    for qp in _quote_check(body):
        lv = "ERROR" if "未成对" in qp else "INFO"
        problems.append({"level": lv, "rule": "引号规范", "msg": qp})

    # 连续3段首词相同（豁免「」引文/列表项、系统面板等刻意格式，避免把备忘录/清单误判为流水账）
    prev, streak, dup = None, 0, 0
    for p in paras:
        if len(p) < 4:
            streak = 0
            continue
        if p[0] in ("「", "【", "“"):
            streak = 0
            continue
        first = p[:2]
        if first == prev:
            streak += 1
            if streak == 3:
                dup += 1
        else:
            streak = 0
        prev = first
    if dup:
        problems.append({"level": "INFO", "rule": "文字质量",
                         "msg": f"连续3段以上首词相同{dup}处（流水账特征）"})

    sens = [w for w in SENSITIVE_BASIC if w in body]
    if sens:
        problems.append({"level": "ERROR", "rule": "敏感词",
                         "msg": f"命中基础敏感词：{', '.join(sens)}（需复核）"})

    if is_chapter_one:
        opening = body[:600]
        hits = sum(1 for m in ["！", "?", "？", "操", "死", "杀", "任务", "系统",
                               "警告", "抹杀", "身份", "玩家", "NPC", "竟然", "突然"] if m in opening)
        stats["opening_hits"] = hits
        if hits < 3:
            problems.append({"level": "ERROR", "rule": "开篇第一页",
                             "msg": f"前600字冲突/信息密度偏低（命中{hits}项），首屏必须有反差或钩子"})
        hero_pos = body.find("陈默")
        stats["hero_first_pos"] = hero_pos
        if hero_pos < 0 or hero_pos > 300:
            problems.append({"level": "WARN", "rule": "主角出场",
                             "msg": "第一章主角应在300字内出场"})

    score = 100
    for p in problems:
        if p["level"] == "ERROR":
            score -= 8
        elif p["level"] == "WARN":
            score -= 4
        else:
            score -= 1
    if total < WARN_CHARS:
        score -= 5
    if not hooked:
        score -= 4
    if is_chapter_one and stats.get("opening_hits", 99) < 3:
        score -= 4
    score = max(0, min(100, score))
    grade = "S" if score >= 90 else "A" if score >= 80 else "B" if score >= 70 else "C" if score >= 60 else "D"

    return {"title": title, "score": score, "grade": grade, "problems": problems, "stats": stats}


def _cn_chapter(n):
    """数字章号转中文，如 2 -> 二，12 -> 十二"""
    _CN = "零一二三四五六七八九十"
    try:
        n = int(n)
    except (ValueError, TypeError):
        return str(n)
    if n <= 0:
        return str(n)
    if n <= 10:
        return _CN[n]
    if n < 20:
        return "十" + (_CN[n % 10] if n % 10 else "")
    if n < 100:
        tens, ones = n // 10, n % 10
        return _CN[tens] + "十" + (_CN[ones] if ones else "")
    return str(n)


def _has_novel_files(d):
    """判断目录是否是小说目录（含大纲/章节/设定文件）。"""
    try:
        names = [f.name for f in d.iterdir() if f.is_file()]
    except Exception:
        return False
    def _has(pat):
        return any(re.search(pat, n, re.I) for n in names)
    return (
        _has(r"outline.*\.(txt|md)$")
        or _has(r"^chapter[0-9]*.*\.txt$")
        or _has(r"^novel_chapter[0-9]*.*\.txt$")
        or _has(r"^第[0-9一二三四五六七八九十]+章.*\.txt$")
        or _has(r"人物.*\.txt$")
        or _has(r"伏笔.*\.txt$")
    )


def _resolve_quality_dir(path="", first_file=""):
    """质检用：确定小说根目录（跟随输入文件，不再写死 fanqie）。"""
    for src in (path, first_file):
        if not src:
            continue
        p = Path(src)
        if not p.exists():
            continue
        d = p.parent if p.is_file() else p
        cur = d
        for _ in range(5):
            if _has_novel_files(cur):
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent
        return d
    return Path(ROOT) / "downloads" / "fanqie"


def _find_first_chapter_file(base):
    """在当前小说目录找第一章文件，找不到返回 None。"""
    pats = [
        re.compile(r"^chapter[0]*1([^0-9]|$)", re.I),
        re.compile(r"^novel_chapter[0]*1([^0-9]|$)", re.I),
        re.compile(r"^第[0]*1章", re.I),
        re.compile(r"^第一章"),
    ]
    dirs = [base]
    try:
        dirs.append(base.parent)
    except Exception:
        pass
    seen = set()
    for d in dirs:
        try:
            cands = [f for f in d.iterdir() if f.is_file() and f.suffix.lower() == ".txt"]
        except Exception:
            continue
        for f in cands:
            key = str(f.resolve())
            if key in seen:
                continue
            seen.add(key)
            if any(p.search(f.stem) for p in pats):
                return f
    return None


def _collect_chapters(path):
    """收集章节文件：目录=扫描全部 chapter*.txt；文件=单章"""
    p = Path(path)
    files = []
    if p.is_dir():
        candidates = sorted(p.glob("chapter*.txt"))
        if not candidates:
            candidates = sorted(p.glob("novel_chapter*.txt"))
        if not candidates:
            candidates = sorted(p.glob("*.txt"))
        for f in candidates:
            m = re.search(r"(\d+)", f.stem)
            title = f"第{_cn_chapter(m.group(1))}章" if m else f.stem
            files.append((title, f))
    elif p.is_file():
        m = re.search(r"(\d+)", p.stem)
        title = f"第{_cn_chapter(m.group(1))}章" if m else p.stem
        files.append((title, p))
    return files


@register_tool(
    name="novel_quality_check",
    description="番茄小说质检引擎：扫描章节/整本小说，按官方写作方法论评分（章节长度/章末钩子/AI痕迹/对话比例/面板密度/引号规范/敏感词/开篇法则），输出百分制评分与逐章问题清单。用于发布前自查。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "章节文件路径或包含 chapter*.txt 的目录，默认扫描 downloads/fanqie/novel"},
            "first_file": {"type": "string", "description": "第一章文件路径（用于开篇特检，可选）"},
            "save_report": {"type": "boolean", "description": "是否保存Markdown报告", "default": True},
        },
        "required": []
    },
    category="writing",
)
def novel_quality_check(path: str = "", first_file: str = "", save_report: bool = True) -> str:
    """扫描小说章节并输出质检报告"""
    base = _resolve_quality_dir(path, first_file)
    target = Path(path) if path else (base / "novel")
    if not target.exists():
        return f"❌ 路径不存在：{target}"

    files = _collect_chapters(str(target))
    if not files:
        return f"❌ 未找到章节文件：{target}"

    # 第一章特检：仅整本扫描（目录）时插入，单文件复检不插入，避免串入别书第一章
    if target.is_dir():
        first_path = Path(first_file) if first_file else _find_first_chapter_file(base)
        if first_path is not None and first_path.exists():
            files = [(t, f) for t, f in files if f.name != first_path.name]
            files.insert(0, ("第一章", first_path))

    results = []
    for title, f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception as e:
            results.append({"title": title, "score": 0, "grade": "F",
                            "problems": [{"level": "ERROR", "rule": "读取失败", "msg": str(e)}],
                            "stats": {"chars": 0, "dialog_ratio": 0, "hook": False, "system_boxes": 0}})
            continue
        results.append(_scan_chapter(title, text, is_chapter_one=(title == "第一章")))

    # 渲染
    lines = ["# 📋 番茄小说质检报告", ""]
    lines.append("| 章节 | 字数 | 对话占比 | 钩子 | 面板 | 评分 | 评级 |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        s = r["stats"]
        lines.append(f"| {r['title']} | {s['chars']} | {s.get('dialog_ratio',0):.0%} | "
                     f"{'✅' if s.get('hook') else '❌'} | {s.get('system_boxes',0)} | **{r['score']}** | {r['grade']} |")
    avg = sum(r["score"] for r in results) / len(results)
    lines.append(f"\n**平均分：{avg:.1f}**")
    lines.append("")
    lines.append("## 问题清单")
    lines.append("")
    for r in results:
        if not r["problems"]:
            continue
        lines.append(f"### {r['title']}（{r['score']}分）")
        for p in r["problems"]:
            icon = {"ERROR": "🔴", "WARN": "🟡", "INFO": "🟢"}.get(p["level"], "⚪")
            lines.append(f"- {icon} **[{p['rule']}]** {p['msg']}")
        lines.append("")
    lines.append("## AI痕迹统计")
    lines.append("")
    ai_sum = {}
    for r in results:
        for h in r["stats"].get("ai_hits", []):
            key = h.split("×")[0]
            ai_sum[key] = ai_sum.get(key, 0) + 1
    if ai_sum:
        for k, v in sorted(ai_sum.items(), key=lambda x: -x[1]):
            lines.append(f"- {k}：{v}处")
    else:
        lines.append("- 未检测到明显AI痕迹 ✅")
    lines.append("")
    lines.append("## 建议")
    lines.append("")
    low = [r for r in results if r["score"] < 70]
    if low:
        lines.append(f"- 🔴 {len(low)}章低于70分，建议优先修改：{', '.join(r['title'] for r in low)}")
    else:
        lines.append("- ✅ 全部章节≥70分")
    short = [r for r in results if r["stats"]["chars"] < STANDARD_CHARS]
    if short:
        lines.append(f"- ⚠️ {len(short)}章不足2000字：{', '.join(r['title'] for r in short)}")
    nohook = [r for r in results if not r["stats"].get("hook")]
    if nohook:
        lines.append(f"- ⚠️ {len(nohook)}章缺章末钩子：{', '.join(r['title'] for r in nohook)}")

    report = "\n".join(lines)

    # 全书一致性检查（前后用词统一）
    try:
        _chapters = [(t, Path(f).read_text(encoding="utf-8")) for t, f in files]
        _cons = run_consistency_check(_chapters)
        report += "\n".join(render_consistency(_cons))
    except Exception as e:
        report += "\n\n⚠️ 一致性检查失败：{0}".format(e)

    if save_report:
        out = base / "quality_report_latest.md"
        out.write_text(report, encoding="utf-8")
        return report + f"\n\n📁 报告已保存：{out}"
    return report


# ============ 模块②：章节生成器（写作蓝图） ============

_OUTLINE_PATH = Path(ROOT) / "downloads" / "fanqie" / "outline_230chapters.md"
_CHAPTER1_PATH = Path(ROOT) / "downloads" / "fanqie" / "chapter1_v2.txt"
_NOVEL_DIR_PATH = Path(ROOT) / "downloads" / "fanqie" / "novel"

_AI_BAN_WORDS = [
    "深吸一口气", "倒吸一口凉气", "倒吸一口冷气", "心头一沉", "心头一紧",
    "心头一跳", "心里咯噔", "浑身一震", "头皮发麻", "后背发凉", "汗毛倒竖",
    "瞳孔骤缩", "缓缓", "默默", "良久", "久久", "静默", "沉默片刻",
    "若有所思", "意味深长", "静静地看着", "宿命", "注定的", "命运的齿轮",
    "灵魂深处", "人生的意义", "不忘初心",
]
_AI_BAN_PATTERNS = [
    (r"像[^。！？\n]{0,12}(一样|一般|似的)", "比喻堆砌，全章最多1个"),
    (r"如同[^。！？\n]{0,12}(一般|一样)", "比喻堆砌，全章最多1个"),
    (r"仿佛[^。！？\n]{0,12}(一般|一样)", "比喻堆砌，全章最多1个"),
]
_DIALOG_TAGS = ["喊", "吼", "嚷", "嘟囔", "嘀咕", "喃喃", "冷哼", "嗤笑",
                "接话", "插嘴", "应声", "咬牙", "压低声音", "扯着嗓子",
                "反问", "追问", "打断", "附和", "劝", "吼回去"]
# 角色名与设定红线不再硬编码，改为从用户自己的小说设定文件动态读取。
# （历史 bug：此处曾硬编码另一部小说的角色「陈默/黄毛/秦朗/系统面板」，
#   导致给《偏差》写蓝图时串味。现已修复为动态加载。）

_NOVEL_SETTING_FILES = [
    "人物定妆图设定.txt", "人物设定.txt", "定妆图提示词_江辰_老周.txt",
    "主线伏笔投放表.txt", "伏笔表.txt", "伏笔投放表.txt",
]


def _find_novel_dir(outline="", prev_chapter=""):
    """确定小说根目录（含 人物设定/伏笔表/大纲 的目录）。

    优先级：outline 参数目录 > prev_chapter 参数目录 > 默认模板目录。
    """
    for src in (outline, prev_chapter):
        if not src:
            continue
        p = Path(src)
        try:
            if p.exists():
                d = p.parent if p.is_file() else p
                if _has_novel_files(d):
                    return d
        except Exception:
            continue
    return _OUTLINE_PATH.parent


def _has_novel_files(d):
    """目录下是否存在小说设定文件（人物设定/伏笔表/大纲）"""
    try:
        names = [f.name for f in d.iterdir() if f.is_file()]
    except Exception:
        return False
    return any(
        any(key in fn for key in ("人物", "定妆", "伏笔", "大纲", "outline", "设定"))
        for fn in names
    )


def _extract_characters(text):
    """从人物定妆图设定文件提取角色名（如「一、江辰（男主）」→ 江辰）"""
    chars, seen = [], set()
    skip = ("清单", "制作", "模板", "用途", "使用", "提示词", "生图", "画风",
            "优先级", "规范", "通用", "命名", "保存")
    for line in text.splitlines():
        m = re.match(r"^[一二三四五六七八九十0-9]+[、.．]([^（(：:，,\s/]{2,12})", line.strip())
        if not m:
            continue
        name = m.group(1).strip()
        if not name or name in seen or any(k in name for k in skip):
            continue
        chars.append(name)
        seen.add(name)
    return chars


def _load_characters(novel_dir):
    """加载本书角色名列表；找不到则返回空列表（蓝图会提示人工补充）"""
    for fn in _NOVEL_SETTING_FILES:
        p = novel_dir / fn
        if not p.exists():
            continue
        try:
            chars = _extract_characters(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if chars:
            return chars
    return []


def _extract_redlines(text):
    """从主线伏笔投放表提取设定红线：三条主线悬念(A/B/C) + 伏笔投放原则"""
    lines = []
    m = re.search(r"【三条主线悬念[^】]*】(.+?)【伏笔投放原则", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            s = line.strip()
            if re.match(r"^[ABC]\.", s):
                lines.append(s)
            elif s.startswith("答案：") and lines:
                lines[-1] = lines[-1] + " " + s
    m2 = re.search(r"【伏笔投放原则[^】]*】(.+?)(?:={10,}|\Z)", text, re.S)
    if m2:
        for line in m2.group(1).splitlines():
            s = line.strip()
            if re.match(r"^\d\.", s):
                lines.append(s)
    return lines


def _load_redlines(novel_dir):
    """加载本书设定红线；找不到则返回空列表"""
    for fn in _NOVEL_SETTING_FILES:
        p = novel_dir / fn
        if not p.exists():
            continue
        try:
            lines = _extract_redlines(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if lines:
            return lines
    return []


def _find_outline_file(novel_dir):
    """在小说目录下找大纲文件（多部小说按目录隔离）"""
    candidates = [
        "novel_outline.txt", "novel_outline.md",
        "outline_230chapters.md", "outline_10chapters.txt",
        "大纲.txt", "细纲.txt", "outline.txt", "outline.md",
    ]
    for c in candidates:
        p = novel_dir / c
        if p.is_file():
            return p
    try:
        for f in sorted(novel_dir.iterdir()):
            if f.is_file() and "outline" in f.name.lower() and f.suffix.lower() in (".txt", ".md"):
                return f
    except Exception:
        pass
    return None


def _read_outline_text(novel_dir):
    p = _find_outline_file(novel_dir)
    if p is not None:
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            pass
    try:
        return _OUTLINE_PATH.read_text(encoding="utf-8")
    except Exception:
        return ""


def _extract_goal(outline_text, n):
    if not outline_text:
        return ""
    m = re.search(rf"[-*]\s*\*\*第{n}章[^*]*\*\*[：:]\s*([^\n]+)", outline_text)
    return m.group(1).strip() if m else "（细纲中未找到该章要点，请依据上下文自行设计）"


def _find_prev_chapter(n, novel_dir):
    """在小说目录下找第 n-1 章文件（兼容 novel_chapterNN / chapterNN / 第N章 命名）"""
    prev = n - 1
    if prev < 1:
        return None
    cands = []
    for fmt in (f"novel_chapter{prev:02d}.txt", f"novel_chapter{prev}.txt",
                f"chapter{prev:02d}.txt", f"chapter{prev}.txt", f"第{prev}章.txt"):
        cands.append(novel_dir / fmt)
    if prev == 1:
        cands += [novel_dir / "chapter1_v2.txt", novel_dir / "chapter1.txt",
                  novel_dir / "chapter01.txt", novel_dir / "novel_chapter1.txt"]
    sub = novel_dir / "novel"
    if sub.is_dir():
        cands += [sub / f"chapter{prev:02d}.txt", sub / f"chapter{prev}.txt"]
    for p in cands:
        if p.is_file():
            return p
    try:
        pat = re.compile(rf"chapter_{prev:02d}|chapter_{prev}(?![0-9])|chapter{prev:02d}|第{prev}章")
        for f in novel_dir.iterdir():
            if f.is_file() and pat.search(f.name):
                return f
    except Exception:
        pass
    return None


def _prev_tail(n, novel_dir, tail_paras=3):
    if n <= 1:
        return "（无上一章，本章为开篇）"
    p = _find_prev_chapter(n, novel_dir)
    if p is None and n <= 2:
        p = _CHAPTER1_PATH
    if p is None and n > 2:
        p = _NOVEL_DIR_PATH / f"chapter{n-1:02d}.txt"
    if p is None or not p.exists():
        return "（无上一章，本章为开篇）"
    paras = [s.strip() for s in p.read_text(encoding="utf-8").split("\n") if s.strip()]
    paras = [s for s in paras if not re.match(r"^第[一二三四五六七八九十百0-9]+章", s)
             and not re.match(r"^第[一二三四五六七八九十百0-9]+章·完", s)]
    return "\n".join(paras[-tail_paras:])


def _build_blueprint(n, outline_text, prev_tail, goal, novel_dir):
    beats = [
        ("开头钩子（前2-3段）",
         "承接上一章结尾的悬念，立刻推进。前400字内必须出现新信息或冲突升级（官方第一页法则：读者第一页看不到反差就划走）。"),
        ("节拍① 推进+小爽点（约1/4处）",
         "对话流推进剧情，给一个小回报：新线索/技能/认可/反转信息。对话占比建议40%+，多用喊/吼/嘟囔/冷哼等标签，少用'说'。"),
        ("节拍② 阻碍/反转（约1/2处）",
         "好事必生变。危机升级、人物暴露秘密、新敌人出现、代价浮出水面。这是留住追读的关键。"),
        ("节拍③ 情绪高潮（约3/4处）",
         "对质/抉择/牺牲/真相碎片。写情绪靠动作和对话，不靠'心头一沉'类模板。"),
        ("章末钩子（最后2-3段）",
         "官方80/20法则：本章解决80%，留20%悬念给下一章。结尾必须出现：新问题/新人物/新真相/倒计时/反转，最后一句话最好带问号或未知感。"),
    ]
    avoid_list = "\n".join(f"- {w}" for w in _AI_BAN_WORDS)
    avoid_pat = "\n".join(f"- {p}（{d}）" for p, d in _AI_BAN_PATTERNS)
    tags = "、".join(_DIALOG_TAGS)

    chars = _load_characters(novel_dir)
    redlines = _load_redlines(novel_dir)
    char_block = "\n".join("- " + c for c in chars) if chars else \
        "- （未找到人物设定文件，请人工补充本书角色）"
    redline_block = "\n".join("- " + r for r in redlines) if redlines else \
        "- （未找到主线伏笔投放表，请人工补充本书设定红线）"

    bp = f"""# 第{n}章 写作蓝图（模块②章节生成器）

> 依据：番茄官方《开篇设计》《钩子设计》《大纲与节奏》方法论
> 目标：净字符 2000~2300（不含标题/结尾标记）

## 一、续写起点（上一章结尾）
{prev_tail}

## 二、本章剧情目标
{goal}

## 三、黄金节奏点（5拍骨架）
"""
    for i, (name, desc) in enumerate(beats, 1):
        bp += f"\n### 拍{i}：{name}\n{desc}\n"

    bp += f"""
## 四、出场角色（全书已存在，禁止改名/改身份）
{char_block}

## 五、设定红线
{redline_block}

## 六、章末钩子要求
- 最后一段必须是悬念/新信息/反转，禁止以场景描写或'他叹了口气'收尾
- 末尾留一句话钩子（问句/未知信息/倒计时/突然出现）

## 七、防AI痕迹清单（写完自查）
禁用词：\n{avoid_list}
禁用句式：\n{avoid_pat}
对话标签至少用3种以上（可选：{tags}）
全章比喻≤1个；段落≤120字；不写空洞升华（宿命/意义/初心）
另6类软痕迹自查（质检引擎会报，写作时主动避开）：
- 金句点题≤3个（"原来/其实/所以"开头下结论的短句别独立成段，融入叙述）
- 破折号悬置≤2次（别老"话说一半——"吊胃口）
- 忌三段式排比（是A、是B、是C的工整句式打散）
- 忌直白点题（原来/其实/这意味着，作者别跳出来下结论）
- 单段台词≤60字（配角别说太长像递证据）
- 「我」开头段落≤12个（第一人称主语别重复）

## 八、字数与格式
- 净字符 2000~2300（质检引擎按此判定）
- 中文引号成对；标题行格式：第{n}章 XXX；结尾加：第{n}章·完
"""
    return bp


@register_tool(
    name="novel_chapter_blueprint",
    description="番茄小说章节生成器（模块②）：读取230章细纲+上一章正文结尾，按官方黄金节奏点+章末钩子公式生成章节写作蓝图（续写起点/剧情目标/5拍骨架/出场角色/设定红线/防AI痕迹清单）。AI按蓝图写正文后调用 novel_quality_check 完成生成→质检→修改闭环。",
    parameters={
        "type": "object",
        "properties": {
            "chapter": {"type": "integer", "description": "章号，如18"},
            "outline": {"type": "string", "description": "细纲文件路径（可选，默认自动）"},
            "prev_chapter": {"type": "string", "description": "上一章文件路径（可选，默认自动）"},
        },
        "required": ["chapter"]
    },
    category="writing",
)
def novel_chapter_blueprint(chapter: int = 18, outline: str = "", prev_chapter: str = "") -> str:
    """生成第N章写作蓝图，AI据此写正文"""
    n = int(chapter)
    novel_dir = _find_novel_dir(outline, prev_chapter)

    outline_text = ""
    if outline:
        try:
            outline_text = Path(outline).read_text(encoding="utf-8")
        except Exception:
            outline_text = ""
    if not outline_text:
        outline_text = _read_outline_text(novel_dir)

    tail = ""
    if prev_chapter:
        try:
            tail = Path(prev_chapter).read_text(encoding="utf-8")
        except Exception:
            tail = ""
    if not tail:
        tail = _prev_tail(n, novel_dir)

    goal = _extract_goal(outline_text, n)
    return _build_blueprint(n, outline_text, tail, goal, novel_dir)


@register_tool(
    name="novel_platform_rules",
    description="番茄小说作家专区运营规则速查：作品推荐评估条件（横版封面/连续更新3天/8万字）、推荐验证期（7天小流量+10万字转正）、作家专区页面结构与功能导航。写小说/运营前调用，确保符合番茄平台推荐机制。",
    parameters={
        "type": "object",
        "properties": {
            "section": {"type": "string", "description": "查询部分：recommend=作品推荐规则，nav=作家专区页面结构，all=全部（默认）"},
        },
        "required": []
    },
    category="writing",
)
def novel_platform_rules(section: str = "all") -> str:
    """返回番茄作家专区运营规则（抓取自作家专区作品推荐页）"""
    kf = Path(__file__).parent / "knowledge" / "zuojia_zone_rules.md"
    if not kf.exists():
        return "❌ 知识文件不存在：" + str(kf)
    text = kf.read_text(encoding="utf-8")
    if section == "recommend":
        start = text.find("## 二、")
        end = text.find("## 三、")
        return text[start:end if end > start else len(text)].strip()
    if section == "nav":
        start = text.find("## 一、")
        end = text.find("## 二、")
        return text[start:end if end > start else len(text)].strip()
    return text.strip()
