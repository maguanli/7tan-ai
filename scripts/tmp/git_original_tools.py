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
    stats["ai_hits"] = ai_hits
    if ai_hits:
        problems.append({"level": "WARN", "rule": "AI痕迹", "msg": "; ".join(ai_hits[:8])})

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

    # 连续3段首词相同
    prev, streak, dup = None, 0, 0
    for p in paras:
        if len(p) < 4:
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


def _collect_chapters(path):
    """收集章节文件：目录=扫描全部 chapter*.txt；文件=单章"""
    p = Path(path)
    files = []
    if p.is_dir():
        candidates = sorted(p.glob("chapter*.txt"))
        if not candidates:
            candidates = sorted(p.glob("*.txt"))
        for f in candidates:
            m = re.search(r"(\d+)", f.stem)
            title = f"第{m.group(1)}章" if m else f.stem
            files.append((title, f))
    elif p.is_file():
        m = re.search(r"(\d+)", p.stem)
        title = f"第{m.group(1)}章" if m else p.stem
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
    base = Path(ROOT) / "downloads" / "fanqie"
    target = Path(path) if path else (base / "novel")
    if not target.exists():
        return f"❌ 路径不存在：{target}"

    files = _collect_chapters(str(target))
    if not files:
        return f"❌ 未找到章节文件：{target}"

    # 第一章特检
    first_path = Path(first_file) if first_file else (base / "chapter1_v2.txt")
    if first_path.exists():
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
        out = Path(ROOT) / "downloads" / "fanqie" / "quality_report_latest.md"
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
_KEY_ENTITIES = [
    "陈默", "黄毛", "王二毛", "秦朗", "苏晚", "苏航", "李大妈", "王桂芬", "王婶",
    "无面者", "老周", "陈建国", "硬币", "命运硬币", "塔", "塔心", "寿命",
    "00001", "00002", "00000", "七枚碎片", "锚点", "系统", "试炼之塔", "任务",
]


def _read_outline_text():
    try:
        return _OUTLINE_PATH.read_text(encoding="utf-8")
    except Exception:
        return ""


def _extract_goal(outline_text, n):
    if not outline_text:
        return ""
    m = re.search(rf"[-*]\s*\*\*第{n}章[^*]*\*\*[：:]\s*([^\n]+)", outline_text)
    return m.group(1).strip() if m else "（细纲中未找到该章要点，请依据上下文自行设计）"


def _prev_tail(n, tail_paras=3):
    p = _CHAPTER1_PATH if n <= 2 else (_NOVEL_DIR_PATH / f"chapter{n-1:02d}.txt")
    if not p.exists():
        return "（无上一章，本章为开篇）"
    paras = [s.strip() for s in p.read_text(encoding="utf-8").split("\n") if s.strip()]
    paras = [s for s in paras if not re.match(r"^第[一二三四五六七八九十百0-9]+章", s)
             and not re.match(r"^第[一二三四五六七八九十百0-9]+章·完", s)]
    return "\n".join(paras[-tail_paras:])


def _build_blueprint(n, outline_text, prev_tail, goal):
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
{chr(10).join('- ' + e for e in _KEY_ENTITIES[:12])}

## 五、设定红线
- 寿命=任务货币，发任务扣寿命（系统代发翻倍；王婶觉醒+30天补偿）
- 双NPC同城触发清除协议（分开行动可冻结，王婶完成协作任务已解除）
- 硬币=实体锚点，共七枚碎片散落七处锚点（塔心是第一处，第二处在正北幸福小区方向）
- 黄毛（王二毛）：第14章昏迷前留下'他是……'悬念
- 秦朗：系统卧底（第14章自曝），第18章交给陈默一把钥匙后失踪，真假存疑
- 父亲陈建国=上一任真正的NPC（第17章塔心日志），被系统抹杀
- 00000=初代NPC沈砚，遗言'寿命是假的，代价是真的'（第18章）
- 系统提示用【】面板，一章不超过4个，禁止用面板水字数

## 六、章末钩子要求
- 最后一段必须是悬念/新信息/反转，禁止以场景描写或'他叹了口气'收尾
- 末尾留一句话钩子（问句/未知信息/倒计时/突然出现）

## 七、防AI痕迹清单（写完自查）
禁用词：\n{avoid_list}
禁用句式：\n{avoid_pat}
对话标签至少用3种以上（可选：{tags}）
全章比喻≤1个；段落≤120字；不写空洞升华（宿命/意义/初心）

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
    outline_text = _read_outline_text()
    if outline:
        try:
            outline_text = Path(outline).read_text(encoding="utf-8")
        except Exception:
            pass
    goal = _extract_goal(outline_text, n)
    tail = _prev_tail(n)
    if prev_chapter:
        try:
            tail = Path(prev_chapter).read_text(encoding="utf-8")
        except Exception:
            pass
    return _build_blueprint(n, outline_text, tail, goal)
