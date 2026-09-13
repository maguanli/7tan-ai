"""
7Tan 模型（TanModel）— 本地预测引擎 + 言语功能系统

来源：智能生命项目的 WorldSimulationUnit（预测误差驱动内生动机的核心组件）。
能力：
  1) 预测引擎 —— 给定「场景 + 动作」，基于历史决策轨迹预测执行结果：
     置信度、预期是否成功、知识缺口、4 维预测特征向量、学习进度(LP)。
  2) 言语功能系统（SpeechGenerator）—— 把内部状态（感知/记忆/预测/动机/情绪/
     反思/元认知）翻译成自然语言「自述」，让 7Tan 模型能用自己的话开口说话。

本模块自包含（仅依赖标准库 + loguru），记忆主存储为 SQLite 数据库
（data/games.db → tan_model_memory 表），并保留 data/tan_model_memory.json 作为镜像备份。
接入 AI 工作台后，用户在「当前模型」下拉框选中「7Tan模型」即可对话测试。

对话用法：
  - 预测推演：「游戏菜单里点击」「场景=游戏菜单 动作=点击」
  - 自述对话：「你是谁」「你什么感觉」「你记得什么」「你觉得会怎样」
  - 「记录 场景=xx 动作=yy 结果=成功/失败」→ 手动标注一次真实结果（喂给模型学习）
  - 「记忆」查看记忆库状态；「清空」重置记忆；「帮助」查看本说明
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Optional

from loguru import logger


# 7Tan 模型的唯一标识（对应数据库 ai_configs 表 config_key 与 model 字段）
T7_MODEL_NAME = "7tan-model"
T7_MODEL_DISPLAY = "7Tan模型"

_MEMORY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "tan_model_memory.json"
_OLD_MEMORY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "world_model_memory.json"

# 场景关键词 → 归一化场景标签（用于自由文本输入）
SCENE_KEYWORDS = [
    ("unknown_interface", ["未知", "unknown", "空白", "桌面", "desktop"]),
    ("game_menu", ["菜单", "menu"]),
    ("main_interface", ["主界面", "首页", "界面", "interface"]),
]
# 动作关键词 → 动作名（顺序即优先级）
ACTION_KEYWORDS = [
    ("scroll", ["滚动", "下滑", "翻页", "scroll"]),
    ("click", ["点击", "单击", "双击", "click"]),
    ("learn", ["学习", "learn"]),
    ("repair", ["修复", "repair", "优化"]),
    ("maintain", ["维持", "存续", "保持", "maintain"]),
    ("explore", ["探索", "explore", "查看", "浏览"]),
]
DEFAULT_SCENE = "unknown_interface"
DEFAULT_ACTION = "explore"


# ---------------- 搜索 query 清洗与结果整理（模块级，供 _clean_search_query/_try_tool_answer 使用） ----------------
# 背景：Bing 对「你会写脚本吗」这类口语长句会降级成单字「你」的结果（搜出来全是「你」字百科），
# 因此必须先把口语清洗成核心关键词（去掉人称代词+能愿动词+疑问/语气词），再交给搜索引擎。

_CMD_PREFIX_RE = re.compile(
    r"^(?:你能帮我|你可以帮我|你能给我|可以帮我|帮我找一下|帮我查一下|帮我搜一下|帮我查查|帮我查|帮我搜|帮我找|帮我|麻烦你|麻烦|请你|请|给我|替我|查找一下|查一下|搜一下|找一下|搜索一下|查询一下|搜索|查找|看看|请问|问一下|我想知道|我想问|告诉我|说说|介绍一下|推荐一下|给我推荐|来一个|来个|想知道|问下|介绍下|说下|讲下)"
)
_PRONOUN_MODAL_RE = re.compile(
    r"(?:你|您|我|我们|你们|咱们|人家)(?:会不会|能不能|可不可以|知不知道|认不认识|会|能|可以|知道|认识|了解|想|想要|需要|打算|觉得)(?:不)?"
)
_MODAL_ANY_RE = re.compile(r"(?:会不会|能不能|可不可以|知不知道|认不认识)")
_PRONOUN_HEAD_RE = re.compile(r"^(?:你|您|我|我们|你们|咱们|人家)")
_MODAL_HEAD_RE = re.compile(r"^(?:会|能|可以|想|想要|需要|会不会|能不能|可不可以)")
_TAIL_PUNCT_RE = re.compile(r"[？?。！!，,、；;：:]+$")
_TAIL_PARTICLE_RE = re.compile(r"(?<!什)(吗|呢|么|啊|呀|吧|哦|哈|呗|啦|咯|喔)+$")
_TAIL_QWORD_RE = re.compile(r"(?:是谁|是什么|是啥|是干什么的|是干嘛的|是做什么的)$")
_HEAD_QWORD_RE = re.compile(r"^(?:什么是|是什么|是谁|为什么|为啥|为何|怎么样|怎么|如何|是不是|有没有|有哪些|哪里|哪儿|多少|几点|几号|干嘛|干吗|做什么|谁|啥)")
_SEARCH_ITEM_RE = re.compile(r"^\s*\d+\.\s+\*\*(.+?)\*\*")
_SEARCH_STOP_TERMS = {
    "什么", "怎么", "如何", "我们", "你们", "咱们", "人家", "这个", "那个",
    "一个", "一下", "可以", "知道", "认识", "还有", "哪些", "是不是", "有没有",
    "不会", "不能", "不想", "为什么", "怎么样", "是吗", "好吗", "吗", "呢",
    "么", "啊", "呀", "吧", "哦", "哈", "咯", "啦", "喔", "啥",
}




def normalize_search_query(text: str) -> str:
    """把用户口语/祈使句清洗成搜索引擎可用的核心查询词。

    去掉：人称代词+能愿动词（你会/你知道/你能…）、祈使/客套前缀（帮我/请…）、
    疑问引导词（是什么/怎么…）、句末语气词（吗/呢…）。清洗不出有效词则返回空串。
    """
    q = (text or "").strip()
    if not q:
        return ""
    for _ in range(5):
        old = q
        q = _PRONOUN_MODAL_RE.sub("", q)
        q = _MODAL_ANY_RE.sub("", q)
        q = _CMD_PREFIX_RE.sub("", q)
        q = _PRONOUN_HEAD_RE.sub("", q)
        q = _MODAL_HEAD_RE.sub("", q)
        q = _TAIL_PUNCT_RE.sub("", q)
        q = _TAIL_QWORD_RE.sub("", q)
        q = _TAIL_PARTICLE_RE.sub("", q)
        q = _HEAD_QWORD_RE.sub("", q)
        q = q.strip(" ？?。，,、:：;；!！…·\"'“”‘’（）()【】[]")
        if q == old:
            break
    # 保留完整问句主体，不再剥离疑问框架词（避免把事实性问题拆散导致跑偏）
    q = re.sub(r"\s+", " ", q).strip(" ？?。，,、:：;；!！")
    q = q.replace("有多少", "有几")  # Bing 对「有几」比「有多少」检索更敏感，能命中数量答案
    if len(q.replace(" ", "")) < 2:
        return ""
    return q[:60]


def extract_query_terms(query: str) -> list:
    """提取 query 的中文/英文关键词（含 2 字滑窗），用于搜索结果相关性判断。"""
    q = normalize_search_query(query) or (query or "")
    terms = set()
    for s in re.findall(r"[\u4e00-\u9fa5]{2,}", q):
        terms.add(s)
        for i in range(len(s) - 1):
            terms.add(s[i:i + 2])
    for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9_.\-]{1,}", q):
        terms.add(t)
    terms = {t for t in terms if len(t) >= 2 and t not in _SEARCH_STOP_TERMS and not t.isdigit()}
    return sorted(terms)


def pick_core_query(query: str) -> str:
    """从清洗后的 query 提取最核心的搜索词：最长中文段 + 英文/数字 token。"""
    q = (query or "").strip()
    if not q:
        return ""
    segs = re.findall(r"[\u4e00-\u9fa5]{2,}", q)
    en = re.findall(r"[A-Za-z0-9][A-Za-z0-9_.\-]{1,}", q)
    core = max(segs, key=len) if segs else ""
    if en:
        core = (" ".join(en) + " " + core).strip()
    return core


def search_text_off_topic(res_text: str, terms: list) -> bool:
    """若所有结果标题都不含任一关键词 → 判定搜索跑偏（如 Bing 把句子降级成单字结果）。"""
    if not res_text or not terms:
        return False
    titles = [m.group(1) for m in re.finditer(r"^\s*\d+\.\s+\*\*(.+?)\*\*", res_text, re.M)]
    if not titles:
        return False  # 非标准 markdown，不做跑偏判定
    for ti in titles:
        for tm in terms:
            if tm and (tm in ti or ti in tm):
                return False
    return True


def filter_search_text(res_text: str, terms: list, keep: int = 4) -> str:
    """整理搜索结果：只保留标题含任一关键词的条目（最多 keep 条）；解析失败/全无关时返回原文。"""
    if not res_text or not terms:
        return res_text
    lines = res_text.split("\n")
    header, blocks, cur_title, cur_lines = [], [], None, []
    for ln in lines:
        m = _SEARCH_ITEM_RE.match(ln)
        if m:
            if cur_title is not None:
                blocks.append((cur_title, cur_lines))
            cur_title, cur_lines = m.group(1), [ln]
        elif cur_title is None:
            header.append(ln)
        else:
            cur_lines.append(ln)
    if cur_title is not None:
        blocks.append((cur_title, cur_lines))
    if not blocks:
        return res_text
    keep_blocks = [(ti, ls) for ti, ls in blocks
                   if any(tm and (tm in ti or ti in tm) for tm in terms)]
    if not keep_blocks:
        return ""   # 全部条目与关键词无关 → 返回空，由上层决定诚实回复/重搜
    if len(keep_blocks) == len(blocks):
        return res_text
    out = "\n".join(header).rstrip()
    for _, ls in keep_blocks[:keep]:
        out += "\n\n" + "\n".join(ls)
    return out


# ---------------- 问句语义解析器（路径A：纯规则，理解疑问类型 + 主体，无第三方模型） ----------------
# 背景：之前只靠正则「删词」生成搜索 query，无法理解「太阳系有多少颗行星」这类常识问答，
# 导致 Bing 把整句降级成单字「太阳」/「大」等跑偏结果。现在加一层问句结构解析：
#   识别疑问类型（数量/定义/身份/位置/时间/原因/怎么做/是否）→ 提取主体 → 生成检索友好 query → 答案抽取。

_MEASURE_RE = r"个|只|颗|条|台|辆|座|位|岁|种|类|张|把|支|根|块|片|本|份|场|次|遍|层|年|天|小时|分钟|秒|米|公里|千克|公斤|克|斤|吨|元|块钱|毛|角|分"
_QUESTION_PARTICLE_RE = re.compile(r"(?<!什)(?<!怎)(吗|呢|么|啊|呀|吧|哈|哦|喔|呗|啦|咯)+$")
_CN_NUM_RE = r"(?:[0-9]+|[一二两三四五六七八九十百千]+)"


class QuestionParse:
    """问句解析结果：疑问类型 + 主体 + 范围 + 量词（纯规则，无模型）。"""

    __slots__ = ("qtype", "scope", "subject", "measure")

    def __init__(self, qtype, scope="", subject="", measure=""):
        self.qtype = qtype
        self.scope = scope or ""
        self.subject = subject or ""
        self.measure = measure or ""

    def is_self_referential(self) -> bool:
        """主体指向「我自己/系统」而非外部常识 → 走原言语层，不走常识问答。"""
        blob = self.scope + self.subject
        return any(k in blob for k in ("你", "我", "自己", "7tan", "模型", "系统"))

    def build_search_query(self) -> str:
        s, sub = self.scope.strip(), self.subject.strip()
        if self.qtype == "quantity":
            if self.measure:
                return f"{s} 有几{self.measure} {sub}".strip()
            return f"{s} {sub} 数量".strip()
        if self.qtype == "definition":
            return f"{sub} 是什么".strip()
        if self.qtype == "identity":
            return sub  # 「X 是谁」→ 直接搜「X」：Bing 对「是谁」后缀会降级成单字
        if self.qtype == "location":
            return f"{sub} 在哪里".strip()
        if self.qtype == "time":
            return f"{sub} 什么时候".strip()
        if self.qtype == "reason":
            return f"为什么 {sub}".strip()
        if self.qtype == "how_to":
            return f"如何 {sub}".strip()
        if self.qtype == "yes_no":
            return f"{sub} {self.scope}".strip()
        return sub


def _parse_quantity(t: str):
    m = re.search(r"(多少|几)", t)
    if not m:
        return None
    scope = t[:m.start()]
    rest = t[m.end():]
    scope = re.sub(r"(有|一共|总共|共计|共|加起来|总计|总)$", "", scope).strip()
    scope = re.sub(r"^(请问|问下|我想知道|想知道|你知道|知道)", "", scope).strip()
    measure, subject = "", rest.strip()
    mm = re.match(r"^(" + _MEASURE_RE + r")(.*)$", rest)
    if mm:
        measure = mm.group(1)
        subject = mm.group(2).strip()
    subject = re.sub(r"(有|是|为|共|一共|总共|总)+$", "", subject).strip()
    subject = re.sub(r"[的了着呢]+$", "", subject).strip()
    subject = re.sub(r"^(有|是|为)+", "", subject).strip()
    if not subject and not scope:
        return None
    return QuestionParse("quantity", scope=scope, subject=subject, measure=measure)


def parse_question(text: str):
    """问句语义解析：识别疑问类型并提取主体。无法识别则返回 None（回退原逻辑）。"""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"[？?。！!，,、；;：:]+$", "", t)
    t = _QUESTION_PARTICLE_RE.sub("", t)
    p = _parse_quantity(t)
    if p:
        return p
    m = re.search(r"(?:什么|啥)是(.+)$", t)
    if m:
        return QuestionParse("definition", subject=m.group(1).strip())
    m = re.search(r"^(.{1,20}?)(?:是什么|是啥|是什么意思|指什么|叫什么|含义是什么)$", t)
    if m:
        return QuestionParse("definition", subject=m.group(1).strip())
    m = re.search(r"^(.{1,20}?)(?:是谁|是什么人|是哪位)$", t)
    if m:
        return QuestionParse("identity", subject=m.group(1).strip())
    m = re.search(r"^(.{1,20}?)(?:在哪|在哪里|在哪儿|什么地方|哪个地方|在什么地方)$", t)
    if m:
        return QuestionParse("location", subject=m.group(1).strip())
    m = re.search(r"^(.{1,20}?)(?:什么时候|何时|哪天|哪一年)$", t)
    if m:
        return QuestionParse("time", subject=m.group(1).strip())
    m = re.search(r"^(?:为什么|为啥|为何|凭什么)(.+)$", t)
    if m:
        return QuestionParse("reason", subject=m.group(1).strip())
    m = re.search(r"^(?:怎么|如何|怎样|咋)(?:做|办|弄|搞|写|处理)?(.+)$", t)
    if m and m.group(1).strip():
        return QuestionParse("how_to", subject=m.group(1).strip())
    m = re.search(r"^(.{1,20}?)(?:是不是|有没有|能不能|会不会|可不可以|是否)(.+)?$", t)
    if m:
        return QuestionParse("yes_no", subject=m.group(1).strip(), scope=(m.group(2) or "").strip())
    return None


def extract_quantity_answer(qp: "QuestionParse", res_text: str):
    """从搜索结果里抽取「数字 + 量词 + 主体」答案片段（如「8颗行星」「八大行星」）。

    优先级：阿拉伯数字 > 中文数字。因为「8颗行星」比「九大行星（传统分类）」更精确，
    避免把过时的「九大行星」这类传统说法当成当前答案。
    """
    sub = qp.subject
    if not sub:
        return None
    meas = qp.measure or r"个|颗|只|条|台|辆|座|位|种|类|张|把|支|根|块|片|本|份|场|次|年|天|公里|米|克|斤|吨|元"
    esc = re.escape(sub)
    pat_arabic = re.compile(r"[0-9]+\s*(?:" + meas + r"|大)?\s*" + esc)
    pat_cn = re.compile(r"[一二两三四五六七八九十百千]+\s*(?:" + meas + r"|大)?\s*" + esc)
    for pat in (pat_arabic, pat_cn):
        mm = pat.search(res_text)
        if mm:
            return mm.group(0)
    return None


def is_7tan_model(model_name: str) -> bool:
    """判断模型名是否指向本地 7Tan 模型"""
    m = (model_name or "").strip().lower()
    return m in ("7tan模型", "7tan", "7tan-model", "7tan_model", "7tanmodel", "tan-model",
                 "world-model", "world_model", "worldmodel", "世界模型")


# 兼容旧引用（防止遗漏调用点）
def is_world_model(model_name: str) -> bool:
    return is_7tan_model(model_name)


def ensure_7tan_model_config() -> bool:
    """确保数据库中存在「7Tan模型」配置项（供模型下拉框显示）。

    不抢当前激活模型（is_active=0），仅注册一条本地模型配置。
    若存在旧的「world-model」标识配置，会顺带清理，避免下拉框出现两个重复项。
    """
    try:
        from ..database.db import get_ai_config_by_key, save_ai_config, delete_ai_config
        # 清理旧标识配置（一次性迁移）
        try:
            if get_ai_config_by_key("world-model"):
                delete_ai_config("world-model")
                logger.info("🗑️ 已清理旧标识配置: world-model → 7tan-model")
        except Exception:
            pass
        if get_ai_config_by_key(T7_MODEL_NAME):
            return True
        save_ai_config(
            config_key=T7_MODEL_NAME,
            provider="local_7tan_model",
            model=T7_MODEL_DISPLAY,
            base_url="",
            api_key="",
            context_window=128000,
            max_tokens=16384,
            temperature=0.25,
            is_active=0,
            extra_config={"local": True, "desc": "本地 7Tan 模型预测引擎 + 言语系统"},
        )
        logger.info(f"✅ 已注册 7Tan 模型配置: {T7_MODEL_NAME}")
        return True
    except Exception as e:
        logger.warning(f"注册 7Tan 模型配置失败: {e}")
        return False


# 兼容旧引用
def ensure_world_model_config() -> bool:
    return ensure_7tan_model_config()


class TanModelMemory:
    """7Tan 模型的记忆库：决策轨迹 + 预测误差历史

    持久化：主存储 = SQLite 数据库 data/games.db → tan_model_memory 表；
    同时保留 data/tan_model_memory.json 作为镜像备份（模块D 沙盒回测兼容）。
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = path or _MEMORY_PATH
        self.traces: list = []      # 决策轨迹
        self.pe_history: list = []  # 预测误差历史
        self.knowledge: list = []   # 知识条目（内容型记忆：事实/定义/规则）
        self.load()

    def load(self):
        """加载记忆：优先数据库（主存储）；数据库为空/不可用时从 JSON 文件迁移导入"""
        # ① 尝试从数据库读取（主存储）
        db_data = None
        try:
            from ..database.db import load_tan_model_memory
            db_data = load_tan_model_memory()
        except Exception as e:
            logger.warning(f"7Tan 模型记忆读取数据库失败（回退 JSON）: {e}")
        if db_data is not None and (db_data.get("traces") or db_data.get("pe_history")):
            self.traces = db_data["traces"] or []
            self.pe_history = db_data["pe_history"] or []
            self.knowledge = db_data.get("knowledge") or []
            if not self.traces:
                self._seed_demo_traces()
                self.save()
            return

        # ② 数据库为空/不可用 → 从 JSON 文件加载（含旧记忆文件迁移）
        src = self.path
        migrated = False
        try:
            if not self.path.exists() and _OLD_MEMORY_PATH.exists():
                src = _OLD_MEMORY_PATH
                migrated = True
        except Exception:
            src = self.path

        try:
            if src.exists():
                raw = json.loads(src.read_text(encoding="utf-8"))
                self.traces = raw.get("traces") or []
                self.pe_history = raw.get("pe_history") or []
                self.knowledge = raw.get("knowledge") or []
                if not self.traces:
                    self._seed_demo_traces()
            else:
                self._seed_demo_traces()
            if migrated or not self.path.exists():
                self.save()   # 迁移：写入数据库（主存储）+ JSON 镜像
        except Exception as e:
            logger.warning(f"7Tan 模型记忆加载失败，使用空库: {e}")
            self.traces = []
            self.pe_history = []
            self.knowledge = []

    def save(self):
        """保存记忆：数据库（主存储） + JSON 镜像（备份/兼容模块D 沙盒回测）"""
        try:
            from ..database.db import save_tan_model_memory
            save_tan_model_memory(self.traces, self.pe_history, self.knowledge)
        except Exception as e:
            logger.warning(f"7Tan 模型记忆保存数据库失败: {e}")
        # JSON 镜像备份（模块D 沙盒回测与人工查看仍依赖该文件，保持实时同步）
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"traces": self.traces, "pe_history": self.pe_history,
                      "knowledge": self.knowledge}
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"7Tan 模型记忆 JSON 镜像备份失败: {e}")

    def _seed_demo_traces(self):
        """首次启动预置示例轨迹，让预测立即可用（模拟已有经验）"""
        base = time.time()
        demo = [
            ("unknown_interface", "scroll", True, True, False, True),
            ("unknown_interface", "scroll", True, False, False, True),
            ("unknown_interface", "click", False, False, False, False),
            ("game_menu", "scroll", True, True, False, False),
            ("game_menu", "click", True, False, True, True),
        ]
        self.traces = []
        for i, (scene, action, finished, changed, reduced, gained) in enumerate(demo):
            self.traces.append({
                "scene": scene, "action": action,
                "action_finished": finished, "scene_changed": changed,
                "defect_reduced": reduced, "knowledge_gained": gained,
                "weight_eff": 1.0, "ts": base - len(demo) + i,
            })

    def add_trace(self, scene, action, finished=True, changed=False,
                  reduced=False, gained=False, origin="internal", **extra) -> dict:
        rec = {
            "scene": scene, "action": action,
            "action_finished": bool(finished), "scene_changed": bool(changed),
            "defect_reduced": bool(reduced), "knowledge_gained": bool(gained),
            "weight_eff": 1.0, "ts": time.time(),
            "origin": origin,   # 来源标记：internal=内部推演 / external=用户输入/工具返回
        }
        if extra:
            rec.update(extra)   # 允许携带对话原文等附加字段（供记忆检索展示）
        self.traces.append(rec)
        self.save()
        return rec

    def find_similar(self, scene) -> list:
        return [t for t in self.traces if isinstance(t, dict) and str(t.get("scene")) == scene]

    # ---------------- 内容型记忆：知识库（事实/定义/规则） ----------------
    def add_knowledge(self, key: str, content: str, source: str = "dialog",
                      confidence: float = 1.0) -> dict:
        """新增/更新一条知识。同 key 已存在则更新内容与时间；否则追加。

        key 形如 'user_name' / 'what_is_7tan' / 'capability_boundary'。
        只存客观事实，不存隐私细节；内容截断到 300 字。
        """
        key = (key or "").strip()
        content = (str(content or "").strip())[:300]
        if not key or not content:
            return {}
        now = time.time()
        for k in self.knowledge:
            if k.get("key") == key:
                k["content"] = content
                k["source"] = source
                k["confidence"] = float(confidence)
                k["ts"] = now
                self.save()
                return k
        rec = {"key": key, "content": content, "source": source,
               "confidence": float(confidence), "ts": now}
        self.knowledge.append(rec)
        self.save()
        return rec

    @staticmethod
    def _tokenize(text: str) -> set:
        """分词：中文整词 + 2-gram（让「老马是谁」也能匹配到知识里的「老马」）。"""
        words = set()
        for m in re.findall(r"[\u4e00-\u9fa5]{2,6}|[A-Za-z0-9_]{2,}", text or ""):
            words.add(m)
            if len(m) >= 3:
                for i in range(len(m) - 1):
                    words.add(m[i:i + 2])
        return words

    def search_knowledge(self, query: str) -> list:
        """按关键词在知识库中检索（key/content 重叠匹配），返回命中条目（最多 5 条）。"""
        query = (query or "").strip()
        if not query:
            return list(self.knowledge)
        words = self._tokenize(query)
        if not words:
            return []
        scored = []
        for k in self.knowledge:
            hay = str(k.get("key", "")) + " " + str(k.get("content", ""))
            hit = sum(1 for w in words if w.lower() in hay.lower())
            if hit > 0:
                scored.append((hit, k))
        scored.sort(key=lambda x: (-x[0], -float(x[1].get("confidence", 1.0)),
                                   -float(x[1].get("ts", 0))))
        return [k for _h, k in scored[:5]]

    def search_content(self, query: str) -> list:
        """内容检索：在全部轨迹的原文（user_text/reply/params/result/action）中做关键词匹配。

        返回命中轨迹（按重叠词数降序，最多 5 条）；这是「记得聊过什么」的真实检索入口。
        """
        query = (query or "").strip()
        if not query:
            return []
        words = self._tokenize(query)
        if not words:
            return []
        scored = []
        for t in self.traces:
            if not isinstance(t, dict):
                continue
            hay_parts = [str(t.get("scene", "")), str(t.get("action", "")),
                         str(t.get("user_text", "")), str(t.get("reply", "")),
                         str(t.get("params", "")), str(t.get("result", "")),
                         str(t.get("intent", ""))]
            hay = " ".join(hay_parts)
            hit = sum(1 for w in words if w.lower() in hay.lower())
            if hit > 0:
                item = dict(t)
                item["_overlap"] = hit
                scored.append(item)
        scored.sort(key=lambda x: (-x["_overlap"], -float(x.get("weight_eff", 1.0))))
        return scored[:5]

    def clear(self):
        self.traces = []
        self.pe_history = []
        self.knowledge = []
        self.save()


class TanModel:
    """7Tan 模型预测引擎 — 移植自智能生命 WorldSimulationUnit"""

    def __init__(self, memory: Optional[TanModelMemory] = None):
        self.memory = memory or TanModelMemory()
        self.speech = SpeechGenerator(self)
        self.pragmatic = PragmaticLayer(self)   # 语用层：寒暄/情绪/挫败/时间语境（2026-09-03）
        self._honest_rot = 0                    # 诚实兜底模板轮换计数器（不再一字不差复读）
        self._evolve_lock = threading.Lock()    # 模块D 后台进化互斥锁（防多线程并发进化）
        # ── 模块E/F：无条件启用（无开关） ──
        self.wm = None                       # 模块E：工作记忆
        self.thinking = None                 # 模块E：三层思考
        self.selflearn = None                # 模块F：自我学习闭环引擎
        self._last_predictions: dict = {}    # {(scene,action): feat} 供闭环计算PE
        self._last_record: Optional[dict] = None  # 最近一条真实标注轨迹（闭环观测用）
        # ── 对话上下文记忆（读上下文能力）：最近对话历史，进程级跨消息存活 ──
        self.conversation_history: list = []
        self._history_max = 20
        try:
            from .working_memory import WorkingMemory, ThinkingLayer
            self.wm = WorkingMemory()
            self.thinking = ThinkingLayer(self, self.wm)
            logger.info("🧠 模块E 已启用：工作记忆 + 有限思考层")
        except Exception as e:
            logger.warning(f"模块E 初始化失败（退回原行为）: {e}")
            self.wm = self.thinking = None
        try:
            from .self_learn import SelfLearnEngine
            self.selflearn = SelfLearnEngine(self.memory)
            logger.info("🧪 模块F 已启用：L1记忆级自我学习闭环")
        except Exception as e:
            logger.warning(f"模块F 初始化失败（退回原行为）: {e}")
            self.selflearn = None
        # ── 模块D：自我进化安全底座（Git/沙盒/回退；总开关默认关闭） ──
        self.evolve = None
        try:
            from .self_evolution import MetaEvolutionLayer
            self.evolve = MetaEvolutionLayer(self.memory)
            logger.info("🔧 模块D 已启用：自我进化安全底座（总开关默认关闭）")
        except Exception as e:
            logger.warning(f"模块D 初始化失败（退回原行为）: {e}")
            self.evolve = None
        # ── 本地 LLM 内核已彻底移除（用户决定）──
        # ── 仿生器官框架（15 器官架构，来自 7Tan_All_Organs 蓝图）──
        self.organ_registry = {}
        try:
            from .bionic_organs import init_all_organs, organ_registry, start_organ_heartbeat
            init_all_organs()
            self.organ_registry = organ_registry
            logger.info(f"🫀 仿生器官框架已挂载：{len(organ_registry)} 个器官")
            # ── 阶段六修复4：器官后台心跳（无人对话器官也自主呼吸；ORGAN_HEARTBEAT=0 可关）──
            start_organ_heartbeat(self.memory)
        except Exception as e:
            logger.warning(f"仿生器官框架挂载失败（不影响对话）: {e}")
            self.organ_registry = {}

    def _bump_memory_hit(self, scene, action=None, strength=0.05):
        """记忆命中增强：调用仿生器官 ORG?A 的 module_a_bump（冷热闭环的"热"端）。

        scene 命中时（action=None）增强该场景下所有轨迹；否则精确匹配 (scene, action)。"""
        try:
            from .bionic_organs import module_a_bump
            module_a_bump(self.memory, scene, action, strength)
        except Exception:
            pass

    # ---------------- 预测核心（忠实移植） ----------------
    def virtual_predict(self, scene, action) -> dict:
        """单步推演：基于历史相似轨迹的加权成功率 → 置信度/预期结果/知识缺口"""
        similar = self.memory.find_similar(scene)
        if similar:
            self._bump_memory_hit(scene, None, 0.05)
        result = {
            "scene": scene, "action": action,
            "similar_count": len(similar),
            "confidence": 0.0,
            "expected_success": False,
            "knowledge_gap": False,
        }
        total_w = 0.0
        succ_w = 0.0
        for item in similar:
            w = float(item.get("weight_eff", 1.0))
            if item.get("action_finished"):
                succ_w += w
            total_w += w
        if total_w > 0:
            result["confidence"] = round(succ_w / total_w, 4)
            result["expected_success"] = result["confidence"] > 0.55
        else:
            result["knowledge_gap"] = True  # 无过往经验 → 认知缺口
        return result

    def predict_outcome(self, scene, action):
        """统计 4 维预测特征向量（0~1）。无经验 → (None, True)。"""
        similar = self.memory.find_similar(scene)
        if not similar:
            return None, True
        n = len(similar)
        feat = [
            round(sum(1 for s in similar if s.get("action_finished")) / n, 4),
            round(sum(1 for s in similar if s.get("scene_changed")) / n, 4),
            round(sum(1 for s in similar if s.get("defect_reduced")) / n, 4),
            round(sum(1 for s in similar if s.get("knowledge_gained")) / n, 4),
        ]
        return feat, False

    @staticmethod
    def compute_pe(predict, actual):
        """预测误差 PE = 均值绝对差 ∈ [0,1]；无预测能力 → 1.0"""
        if predict is None or actual is None or len(predict) != len(actual):
            return 1.0
        return round(sum(abs(p - a) for p, a in zip(predict, actual)) / len(predict), 4)

    @staticmethod
    def compute_lp(pe_now, pe_prev):
        """学习进度 LP = PE(t-1) - PE(t)；正值 = 误差下降 = 正在学会"""
        return round(pe_prev - pe_now, 4)

    # ---------------- 对话接口 ----------------
    def respond(self, user_text: str, history: Optional[list] = None) -> str:
        """对话入口（完整思考循环）：吸收上下文 → 思考 → 观察回写 → 模块F tick。

        思考循环（纯算法，不依赖任何外部 API）：
          ① 上下文进入工作记忆（补录历史轮次 / 提取用户名字 / 更新话题）
          ② 意图识别：指令 → 言语自述 → 记忆检索推理 → 预测推演
          ③ 本轮对话写回工作记忆事件链 + 对话经验入库（自我学习）
          ④ 模块F 主循环 tick（假设评估/落地）

        history: 可选，最近对话历史 [{role, content}, ...]（不含当前消息）。
        """
        if history:
            self.conversation_history = list(history[-self._history_max:])
        # ⑥.0 外部信号流入总线（阶段一「我-非我」边界：用户输入 = external 事件）
        try:
            from .bionic_organs import emit_event
            emit_event("user_input", {"text": (user_text or "").strip()}, source="WORLD_MODEL", origin="external")
        except Exception:
            pass
        # ① 上下文进入工作记忆
        self._absorb_context(user_text)
        # ② 思考循环
        reply = self._respond_impl(user_text)
        # ③ 本轮对话观察回写
        self._observe_round(user_text, reply)
        # ④ 模块F 主循环 tick
        if self.selflearn is not None:
            try:
                self.selflearn.f_selflearn_tick()
            except Exception as e:
                logger.warning(f"模块F tick 异常（忽略，不影响回复）: {e}")
        # ⑤ 模块D 自我进化 tick（异步后台执行，不阻塞对话回复；总开关关闭时零开销）
        if self.evolve is not None:
            self._run_evolve_async()
        # ⑥ 仿生器官主循环 tick（启用的器官每轮对话呼吸一次）
        try:
            from .bionic_organs import organ_tick_all
            organ_tick_all(self.memory)
        except Exception as e:
            logger.warning(f"仿生器官 tick 异常（忽略，不影响回复）: {e}")
        # ⑥.5 言语输出器官：把本轮回复写入输出日志（ORG?SPEECH 真实工作）
        try:
            from .bionic_organs import module_speech_push
            module_speech_push(reply)
        except Exception:
            pass
        return reply

    def _run_evolve_async(self) -> None:
        """模块D 自我进化挪到后台线程执行，避免留一法回测 + 沙盒子进程阻塞对话回复。

        非阻塞锁：若上一轮进化仍在后台运行则直接跳过（防线程堆积）。
        进化本身的冷却/配额仍由 MetaEvolutionLayer._can_evolve 控制。
        """
        if not self._evolve_lock.acquire(blocking=False):
            return  # 已有进化线程在跑，跳过
        def _worker():
            try:
                self.evolve.tick()
            except Exception as e:
                logger.warning(f"模块D 后台进化异常（忽略）: {e}")
            finally:
                self._evolve_lock.release()
        try:
            t = threading.Thread(target=_worker, daemon=True, name="7tan-self-evolve")
            t.start()
        except Exception as e:
            self._evolve_lock.release()
            logger.warning(f"模块D 后台线程启动失败（忽略）: {e}")

    # ---------------- 思考循环：上下文吸收 / 观察回写 / 记忆检索推理 ----------------
    def _absorb_context(self, user_text: str) -> None:
        """① 把对话历史吸收进工作记忆：补录事件链、提取用户名字、更新话题。"""
        if self.wm is None:
            return
        try:
            slots = self.wm.dialog_slots
            seen = len(slots.get("recent_events") or [])
            hist = self.conversation_history or []
            # 补录尚未进入事件链的历史轮次
            for m in hist[seen:]:
                role = m.get("role")
                content = (m.get("content") or "").strip()
                if role in ("user", "assistant") and content:
                    self.wm.wm_observe_dialog(role, content)
            # 从历史 + 当前文本提取用户名字（用户侧消息优先）
            for m in list(hist) + [{"role": "user", "content": user_text}]:
                if m.get("role") != "user":
                    continue
                name = self.wm.wm_extract_user_name(m.get("content", ""))
                if name:
                    self.wm.wm_remember_user_name(name)
            # 更新话题
            self.wm.wm_update_topic(user_text)
        except Exception as e:
            logger.warning(f"吸收上下文失败（忽略，不影响回复）: {e}")

    def _observe_round(self, user_text: str, reply: str) -> None:
        """③ 本轮对话写入工作记忆事件链 + 自我学习对话经验入库。"""
        if self.wm is not None:
            try:
                self.wm.wm_observe_dialog("user", user_text)
                self.wm.wm_observe_dialog("assistant", reply)
            except Exception as e:
                logger.warning(f"观察本轮对话失败（忽略）: {e}")
        if self.selflearn is not None:
            try:
                intent = getattr(self.speech, "_last_intent", None)
                self.selflearn.learn_from_dialog(user_text, reply, intent)
            except Exception as e:
                logger.warning(f"对话经验入库失败（忽略）: {e}")
        # ── 阶段六修复3：目标执行结果喂入器官总线 ──
        # 修复前：goal_tag+success 的思想碎片在生产代码中 0 处产生（仅测试脚本注入）→
        # CONSOLIDATE 巩固出的记忆无目标成败标签 → SELFMODEL 无样本可归纳 →
        # selfmodel_update 事件 0 次 → limitations 恒空 → candidate_motives/final_goals 0 次（测试3/4 双断供）。
        # 现在：每轮对话 = 一次「对话:{意图}」目标执行，成败结果压入工作记忆，
        # 由 CONSOLIDATE 巩固 → SELFMODEL 样本驱动提前归纳 → 闭环打通。
        try:
            from .bionic_organs import wm_push_thought
            _intent = getattr(self.speech, "_last_intent", None) or "闲聊"
            _ok = bool((reply or "").strip())
            wm_push_thought(
                f"goal:对话:{_intent} 已执行(结果={'成功' if _ok else '失败'})",
                focus=0.45,
                valence=0.25 if _ok else -0.25,
                origin="internal",
                goal_tag=f"对话:{_intent}",
                success=_ok,
            )
        except Exception:
            pass

    def _respond_impl(self, user_text: str) -> str:
        text = (user_text or "").strip()
        logger.info(f"🌍 7Tan模型 · 收到输入: {text[:80]}")
        if not text:
            return self._usage()
        low = text.lower()
        # 1) 精确指令优先
        if low in ("help", "帮助", "?", "？", "用法"):
            logger.info("🌍 7Tan模型 → 返回用法说明")
            return self._usage()
        if low in ("memory", "记忆", "状态", "status"):
            logger.info("🌍 7Tan模型 → 返回记忆库状态")
            return self._report_memory()
        if low.startswith(("清空", "clear", "重置", "reset")):
            self.memory.clear()
            if self.wm is not None:
                self.wm.reset()  # 会话重置：工作记忆草稿全部销毁（易失性）
            logger.info("🌍 7Tan模型 → 记忆库已清空")
            return "🧹 记忆库已清空。可重新输入场景+动作开始测试。"
        if low.startswith(("记录", "record", "标注")):
            reply = self._handle_record(text)
            logger.info("🌍 7Tan模型 → 已记录真实轨迹（学习）")
            if self.selflearn is not None:
                extra = self._selflearn_after_record()
                if extra:
                    reply = reply + "\n" + extra
            return reply
        # 2) 言语层（自述类问题）
        speech = self.speech.respond(text)
        if speech is not None:
            logger.info(f"🌍 7Tan模型 → 言语自述（意图={self.speech._last_intent}）")
            return speech
        # 2.3) 语用层（寒暄/时间语境/情绪/挫败/名字确认）：接住「说人话」的输入，
        #      不再掉进联网搜索兜底或一字不差的固定模板（2026-09-03 修复「程序化回复」）
        try:
            prag = self.pragmatic.respond(text)
        except Exception as e:
            logger.warning(f"语用层异常（忽略，走原链路）: {e}")
            prag = None
        if prag is not None:
            logger.info(f"🌍 7Tan模型 → 语用回应（语用={self.pragmatic._last_pragma}）")
            return prag
        # 2.5) 长期记忆库优先（新知识压旧）：先从 memory_library 检索内容型知识，避免旧事实条目拦截
        lm_hits = self._search_longterm_memory(text)
        if lm_hits:
            logger.info(f"🌍 7Tan模型 → 长期记忆命中 {len(lm_hits)} 条（新知识）")
            lines = ["📚 我在长期记忆里找到了相关的知识："]
            for m in lm_hits[:5]:
                t = (m.get("thought") or "").strip()
                shown = t if len(t) <= 90 else t[:90] + "…"
                lines.append(f"   · {shown}")
            lines.append("")
            lines.append("这是我真正记住的知识，不是现编的。")
            return "\n".join(lines)
        # 2.6) 旧知识库兜底：事实条目（用户身份/定义/边界）
        k_hits = self.memory.search_knowledge(text)
        if k_hits:
            logger.info(f"🌍 7Tan模型 → 知识库命中 {len(k_hits)} 条（内容型记忆）")
            lines = ["📌 这个问题我知识库里有答案（来自真实对话提取）："]
            for k in k_hits[:3]:
                lines.append(f"   · {k.get('content', '')}")
            if len(k_hits) > 3:
                lines.append(f"   ……（还有 {len(k_hits) - 3} 条相关）")
            lines.append("")
            lines.append("这是我从之前对话里抽出来并固化的事实，不是现编的。")
            return "\n".join(lines)
        # 3) 疑问句 → 记忆类问题走思考循环（检索真实记忆）；常识/闲聊优先本地 LLM 大脑
        if self._is_question(text):
            # 本地 LLM 已移除：疑问句统一走思考循环（记忆检索推理）
            logger.info("🌍 7Tan模型 → 疑问句走思考循环（记忆检索推理）")
            return self._think_answer_question(text)
        # 4) 默认：预测推演（仅当文本真的像推演请求；否则诚实承认不会，不硬答）
        if self._looks_like_prediction_request(text):
            scene, action = self._parse_scene_action(text)
            if self.thinking is not None:
                logger.info(f"🌍 7Tan模型 → 思考层推演（场景={scene} 动作={action}）")
                return self._report_predict_with_thinking(scene, action)
            logger.info(f"🌍 7Tan模型 → 预测推演（场景={scene} 动作={action}）")
            return self._report_predict(scene, action)
        # 4.5) 工具增强：非疑问请求（如「统计 data 目录」「查新闻」）也先尝试调用工具
        tool_reply = self._try_tool_answer(text)
        if tool_reply:
            logger.info("🌍 7Tan模型 → 未识别意图，转工具实时查证")
            return tool_reply
        # 5) 都不是 → 诚实承认（不编、不强行推演）
        logger.info("🌍 7Tan模型 → 未识别请求，诚实承认不会")
        return self._honest_unknown(text)

    def _looks_like_prediction_request(self, text: str) -> bool:
        """判断文本是否真的像预测推演请求（而不是乱问/闲聊）。"""
        if re.search(r'(?:场景|scene)\s*[=:：]', text) or re.search(r'(?:动作|action|act)\s*[=:：]', text):
            return True
        for _scene_kw, words in SCENE_KEYWORDS:
            if any(w in text for w in words):
                return True
        for _act_kw, words in ACTION_KEYWORDS:
            if any(w in text for w in words):
                return True
        # 自由文本式（「游戏菜单里点击」「unknown_interface 滚动」）
        if any(w in text for w in ("点击", "单击", "双击", "滚动", "下滑", "翻页",
                                   "查看", "浏览", "修复", "优化", "维持", "存续",
                                   "探索", "学习")):
            return True
        return False

    # ---------------- 工具调用层（模块G：主模型调用只读工具查证，不硬答） ----------------
    def _call_tool_safe(self, name: str, args: dict):
        """调用系统工具注册表执行工具；失败/无结果返回 None（绝不抛异常影响对话）。"""
        try:
            from ..tools.registry import execute_tool
            result = execute_tool(name, args or {})
            if result is None:
                return None
            s = str(result)
            if s.startswith("❌"):
                return None
            # （阶段六修复5）tool_result 事件已集中到 registry._feed_tan_model 统一发出
            # （带 ok 成败标志），此处不再重复发，避免同一执行双计数。
            return s
        except Exception as e:
            logger.warning(f"🔧 7Tan模型工具调用异常 {name}: {e}")
            return None

    def _wrap_tool_reply(self, source: str, content: str) -> str:
        """把工具真实返回结果包装成主模型回答（截断防爆，注明工具来源）。"""
        MAX_LEN = 1600
        body = content if len(content) <= MAX_LEN else content[:MAX_LEN] + chr(10) + "……（结果较长，已截断）"
        return chr(10).join([
            f"🔧 这个问题我不在记忆里硬猜——我调用了「{source}」工具实时查证：",
            "",
            body,
            "",
            "（以上是工具返回的真实信息，不是我编的。需要进一步处理可以继续告诉我。）",
        ])

    def _answer_common_question(self, text: str):
        """常识问答（路径A）：问句语义解析 → 检索改写 → 搜索 → 答案抽取。

        纯规则、无第三方模型。识别疑问类型与主体，生成检索友好 query，
        对「数量查询」从搜索结果抽取直接答案（如「8颗行星」），而非甩原始搜索列表。
        解析不出 / 问自己 / 时间日期类 → 返回 None（回退原逻辑）。
        """
        t = (text or "").strip()
        if not t:
            return None
        # 时间/日期类交给 _try_tool_answer 的时间分支（直接系统时间，更准）
        if re.search(r"(几点|时间|日期|星期几|几号|现在.*点)", t):
            return None
        p = parse_question(t)
        if p is None or p.is_self_referential():
            return None
        query = p.build_search_query()
        if not query or len(query.replace(" ", "")) < 2:
            return None
        res = self._call_tool_safe("web_search", {"query": query, "num_results": 8})
        if not res:
            return None
        # 数量查询 → 抽取直接答案
        if p.qtype == "quantity":
            ans = extract_quantity_answer(p, res)
            if ans:
                lead = f"{p.scope}有" if p.scope else "答案是"
                body = res if len(res) <= 900 else res[:900] + "……"
                return chr(10).join([
                    f"🔍 我查证的结果：{lead} {ans}。",
                    "",
                    "（这是我从搜索结果里抽取的直接答案，原始结果如下供核对）",
                    "",
                    body,
                ])
        # 其他类型 → 整理展示相关条目
        shown = filter_search_text(res, extract_query_terms(query))
        if shown and shown.strip():
            return self._wrap_tool_reply("联网搜索", shown)
        return None


    def _try_tool_answer(self, text: str):
        """主模型工具增强层：多工具协同 + 智能降级 + 搜索引擎兜底（不再「命中即停」）。

        流程：
          1. 本地时间（零工具，直接返回）
          2. 识别意图，收集【所有】候选工具调用
          3. 逐个执行，收集有效结果
          4. 资源库查空 → 降级联网搜索；无工具命中 → 联网搜索兜底
          5. 整合结果返回；清洗不出查询词才返回 None（走诚实承认）
        """
        t = (text or "").strip()
        if not t:
            return None
        low = t.lower()
        try:
            # 1) 本地时间/日期（零工具，直接系统时间）
            if re.search(r"(几点|时间|日期|星期几|几号|现在.*点)", t) and not any(k in t for k in ("你", "我", "耗时", "上线", "运行")):
                now = time.strftime("%Y-%m-%d %H:%M:%S")
                wd = {"Mon": "一", "Tue": "二", "Wed": "三", "Thu": "四",
                      "Fri": "五", "Sat": "六", "Sun": "日"}.get(time.strftime("%a"), "?")
                return f"🕐 现在是 {now}，星期{wd}（本机系统时间，真实可靠）。"

            # 2) 收集候选工具调用（一个请求可能触发多个工具，命中不再立即返回）
            calls = []  # (source_label, tool_name, args_dict)

            # 2.1 新闻/资讯类
            if any(k in t for k in ("新闻", "资讯", "最新消息", "行业动态", "新游", "发生了什么")):
                topic = "游戏"
                m = re.search(r"(游戏|手游|Steam|steam|AI|人工智能|科技|财经|数码)", t)
                if m:
                    topic = m.group(1)
                calls.append(("新闻资讯", "fetch_news", {"topic": topic, "count": 5}))

            # 2.2 游戏/软件资源类（查本地资源库）
            if any(k in t for k in ("游戏", "软件", "资源", "下载", "应用", "app")):
                kw = re.sub(r"[？?，。、的有什么哪些推荐一下介绍给我看看帮我找]|(游戏|软件|资源|下载|应用|app|有|吗|呢|么|啥|什么|最新|好玩)", "", t)
                kw = (kw or "").strip()[:20]
                if len(kw) < 2:
                    kw = t[:20]
                calls.append(("7Tan资源库", "db_query_resources", {"keyword": kw, "limit": 5}))

            # 2.3 目录/文件统计类
            if any(k in t for k in ("统计", "列出", "看看", "查看", "数一数", "有几个文件")) and re.search(r"(目录|文件夹|文件|路径)", t):
                root = Path(__file__).resolve().parent.parent.parent
                dir_part = ""
                for seg in re.split(r"[，。；;、]+", t):
                    for token in seg.split():
                        if ":" in token:
                            cand = Path(token)
                            if cand.exists() and cand.is_dir():
                                dir_part = str(cand)
                                break
                    if dir_part:
                        break
                if not dir_part:
                    if "data" in low:
                        dir_part = str(root / "data")
                    elif "下载" in t:
                        dir_part = str(root / "downloads")
                    elif "tmp" in low:
                        dir_part = str(root / "tmp")
                    else:
                        dir_part = str(root / "data")
                calls.append(("文件系统", "list_files", {"directory": dir_part}))

            # 3) 逐个执行，收集有效结果（不再命中即停）
            results = []          # [(source_label, content)]
            resource_empty = False
            for source, name, args in calls:
                res = self._call_tool_safe(name, args)
                if not res or not res.strip():
                    continue
                if name == "db_query_resources" and self._is_empty_db_result(res):
                    resource_empty = True   # 资源库查空，标记待降级
                    continue
                results.append((source, res))

            # 4) 有有效结果 → 整合返回
            if results:
                return self._merge_tool_replies(results)

            # 5) 资源库查空 / 无任何工具命中 → 联网搜索兜底（仅疑问句或明确搜索任务才搜，陈述句/闲聊不搜）
            #    语用层再拦一道：寒暄/情绪/抱怨这类「说人话」的短句，永远不拿去联网搜（防「晚上好」搜出百科）
            _questionish = (self._is_question(t) or any(
                k in t for k in ("搜索", "搜一下", "查一下", "找一下", "是什么", "怎么回事", "介绍", "推荐", "帮我找", "帮我查")))
            _not_smalltalk = not self.pragmatic.is_smalltalk(t)
            if resource_empty or (_questionish and _not_smalltalk):
                query = self._clean_search_query(t)
                if query:
                    res = self._call_tool_safe("web_search", {"query": query, "num_results": 5})
                    if res:
                        src = "联网搜索（资源库无记录，已自动转搜索）" if resource_empty else "联网搜索"
                        # 跑偏检测：Bing 对口语长句会降级成单字结果（如「你会…」→ 全是「你」字百科）→ 用核心词重搜一次
                        terms = extract_query_terms(query)
                        if terms and search_text_off_topic(res, terms):
                            core = pick_core_query(query)
                            if core and core != query:
                                res2 = self._call_tool_safe("web_search", {"query": core, "num_results": 5})
                                if res2:
                                    res = res2
                                    query = core
                                    src = "联网搜索（已按核心词重新搜索）"
                        # 整理：只保留与核心关键词相关的条目再展示
                        shown = filter_search_text(res, extract_query_terms(query))
                        if not shown or not shown.strip():
                            return None   # 过滤后无相关结果 → 走诚实回复
                        return self._wrap_tool_reply(src, shown)
            return None
        except Exception as e:
            logger.warning(f"🔧 7Tan模型工具增强异常（忽略，不影响回复）: {e}")
            return None

    def _is_empty_db_result(self, res: str) -> bool:
        """判断 db_query_resources 是否返回空结果（资源库无记录）。"""
        if not res:
            return True
        return any(k in res for k in ("没有符合条件的资源", "📭", "没有找到", "暂无", "无结果", "0 条"))

    def _clean_search_query(self, text: str) -> str:
        """把用户口语/祈使句清洗成搜索引擎可用的核心查询词（委托模块级 normalize_search_query）。

        关键：必须去掉「人称代词 + 能愿动词」（你会/你知道/你能…）与疑问/语气词，
        否则 Bing 会把「你会写脚本吗」这类句子降级成单字「你」的结果（搜出来全是「你」字百科）。
        """
        return normalize_search_query(text)

    def _merge_tool_replies(self, results: list) -> str:
        """整合多个工具的返回结果为一个回答（多工具协同，择优输出）。"""
        if not results:
            return ""
        if len(results) == 1:
            return self._wrap_tool_reply(results[0][0], results[0][1])
        # 多工具结果合并
        lines = ["🔧 这个问题我不在记忆里硬猜——我同时调用了多个工具查证，综合结果如下：", ""]
        for idx, (source, content) in enumerate(results, 1):
            body = content if len(content) <= 700 else content[:700] + "……（截断）"
            lines.append(f"【{idx}】{source}：")
            lines.append(body)
            lines.append("")
        lines.append("（以上是工具返回的真实信息，不是我编的。）")
        return "\n".join(lines)

    def _honest_unknown(self, text: str) -> str:
        """未识别请求时的诚实回应：不编、不强行推演（多模板轮换，不再一字不差复读）。"""
        heads = [
            "🤖 诚实说：这句话我不认识，工具也查过了没有可靠答案，所以不硬答。",
            "🤖 这句超出了我现在的能力——查证过了没查到，与其胡答不如明说：我不会。",
            "🤖 我接不住这句话。不是装傻，是真不会——查不到的我从不编。",
        ]
        head = heads[self._honest_rot % len(heads)]
        self._honest_rot += 1
        return chr(10).join([
            head,
            "",
            "我能做的（含实时工具查证）：",
            "  · 自述：你是谁 / 你记得什么 / 你什么感觉 / 你会什么",
            "  · 推演：给我「场景 + 动作」，比如「游戏菜单里点击」",
            "  · 学习：你说「记录 场景=xx 动作=yy 结果=成功/失败」",
            "",
            "其他问题，我答不了就是答不了。",
        ])

    @staticmethod
    def _is_question(text: str) -> bool:
        """判断输入是否为疑问句（含疑问标记或疑问词开头）"""
        if any(m in text for m in ("？", "?", "吗", "呢", "么", "怎么", "为什么",
                                   "能不能", "可不可以", "如何", "哪来", "哪",
                                   "是什么", "是谁", "会不会", "干嘛", "干吗", "多少", "几次",
                                   "几个", "哪些", "有哪些", "有没有", "是不是", "啥",
                                   "多远", "多久", "多大", "几大")):
            return True
        head = text[:2]
        if head in ("你", "怎么", "为什么", "如何", "哪", "什么", "谁", "为何", "为啥"):
            return True
        # 「说一下/讲一下/介绍一下 + 你的」也算疑问
        if any(text.startswith(h) for h in ("说一下", "讲一下", "介绍一下", "说说", "聊聊")):
            return True
        return False


    def _fallback_question(self, text: str) -> str:
        """疑问句但未命中任何意图时的兜底引导"""
        return chr(10).join([
            "🤖 这个问题我暂时还接不住——我的言语系统目前只覆盖「我自己」这个主题。",
            "",
            "我能好好聊的，是关于我自己的这几件事：",
            "  · 我是谁 / 我是什么（元认知）",
            "  · 我是怎么来的 / 谁创造的我（来源）",
            "  · 我现在在看什么（感知）",
            "  · 我记得什么（记忆）",
            "  · 我接下来想做什么、为什么（动机）",
            "  · 我什么感觉（情绪）",
            "  · 我判断接下来会怎样（预测）",
            "  · 我做得对不对（反思）",
            "  · 我能做什么 / 我会学习吗（能力）",
            "",
            "如果你想让我做「预测推演」，请给我「场景 + 动作」，比如：",
            "  「游戏菜单里点击」 或 「场景=游戏菜单 动作=点击」",
            "",
            "输入「帮助」查看完整用法。",
        ])

    # 指代词集合：命中则触发「对话回溯」——把上一轮对话内容合并进本轮检索词。
    _COREF_WORDS = (
        "那", "这", "它", "这些", "那些", "它们", "这个", "那个",
        "这么", "那么", "其中", "上面", "刚才说的", "前面说的", "之前说的",
    )

    def _resolve_context_reference(self, text: str) -> str:
        """对话回溯：若当前输入含指代词，则把上一轮用户消息合并进检索词。

        解决短板「缺少对话回溯能力」：例如用户上一句说「我积累了 2236 段经历」，
        下一句问「那这些经历会遗忘吗」，系统能自动关联上一句的「经历」去检索，
        而不是把「这些」当成孤立词、检索落空。无指代词或无上一轮时返回原文本。"""
        if not text or not any(w in text for w in self._COREF_WORDS):
            return text
        for m in reversed(self.conversation_history or []):
            if isinstance(m, dict) and m.get("role") == "user":
                prev = (m.get("content") or "").strip()
                if prev:
                    return f"{prev} {text}"
        return text

    def _think_answer_question(self, text: str) -> str:
        """疑问句思考循环：在工作记忆 + 长期记忆中检索相关经验，能答则答，不能答则诚实承认。

        检索策略：
          1. 工作记忆对话槽位（最近聊了什么 / 用户是谁）—— 回答「我们在聊什么」类
          2. 长期记忆轨迹 —— 把问题中的词与记忆中的场景/动作做关键词重叠匹配
          3. 命中 → 引用真实记忆回答；未命中 → 诚实承认不会，不编答案
        """
        lines: list = []
        # —— 检索-1：指代回溯（对话上下文复用，修复「缺少对话回溯能力」）——
        search_text = self._resolve_context_reference(text)
        # —— 检索0：长期记忆库优先（新知识压旧，倒序检索最新在前）——
        lm_hits = self._search_longterm_memory(search_text)
        if lm_hits:
            lines.append("📚 我在长期记忆里找到了相关的知识：")
            for m in lm_hits[:5]:
                t = (m.get("thought") or "").strip()
                shown = t if len(t) <= 90 else t[:90] + "…"
                lines.append(f"   · {shown}")
            lines.append("")
            lines.append("这是我真正记住的知识，不是现编的。")
            return "\n".join(lines)
        # —— 检索0.5：旧知识库兜底（事实条目，如「老马是谁」「7Tan 是什么」）——
        k_hits = self.memory.search_knowledge(search_text)
        if k_hits:
            lines.append("📌 这个问题我知识库里有答案（来自真实对话提取）：")
            for k in k_hits[:3]:
                lines.append(f"   · {k.get('content', '')}")
            if len(k_hits) > 3:
                lines.append(f"   ……（还有 {len(k_hits) - 3} 条相关）")
            lines.append("")
            lines.append("这是我从之前对话里抽出来并固化的事实，不是现编的。")
            return "\n".join(lines)
        # —— 检索1：工作记忆对话槽位（最近聊了什么） ——
        if self.wm is not None:
            slots = self.wm.dialog_slots
            if any(k in text for k in ("我们", "刚才", "之前", "上面", "聊", "话题", "说哪")):
                if slots.get("recent_events"):
                    last_user = ""
                    for m in reversed(slots["recent_events"]):
                        if m["role"] == "user":
                            last_user = m["content"]
                            break
                    if last_user:
                        lines.append(f"🤔 我检索了工作记忆：最近你跟我说的是「{last_user[:60]}」。")
        # —— 检索2：长期记忆轨迹（关键词重叠） ——
        hits = self._search_memory_by_keywords(search_text)
        weak_memory = []   # 弱相关痕迹（只重叠1个词，疑似撞词），存下待工具查证后整合
        if hits:
            strong = hits[0].get("_overlap", 0) >= 2
            if strong:
                lines.append("📚 我在长期记忆里找到了相关的经历：")
                for h in hits[:2]:
                    sc, ac = h.get("scene", "?"), h.get("action", "?")
                    ok = "成功" if h.get("action_finished") else "失败"
                    ts_hint = h.get("ts_hint", "")
                    lines.append(f"   · 场景「{sc}」动作「{ac}」—— {ok}（{ts_hint}）")
                lines.append("")
                lines.append("这是我真实经历过的，不是编的。你可以让我再推演一次：")
                lines.append(f"  「{hits[0].get('scene', '?')}里{hits[0].get('action', '?')}」")
                return "\n".join(lines)
            # 弱相关：不阻塞，先走工具查证，再把记忆痕迹一起整合给用户
            weak_memory = hits[:2]
        # —— 检索2.4：常识问答（问句语义解析优先）—— 理解疑问类型+主体，抽取直接答案 ——
        common = self._answer_common_question(search_text)
        if common:
            logger.info("🌍 7Tan模型 → 常识问答（问句解析命中）")
            return common
        # —— 检索2.4.5：工具增强 —— 记忆未命中/弱相关时，调用工具实时查证（知识/新闻/文件/联网搜索）
        tool_reply = self._try_tool_answer(search_text)
        if tool_reply:
            if weak_memory:
                logger.info("🌍 7Tan模型 → 记忆弱相关，工具查证 + 记忆痕迹整合")
                hint = "\n".join(
                    f"   · 场景「{h.get('scene', '?')}」动作「{h.get('action', '?')}」" for h in weak_memory
                )
                return ("📚 我记忆里只有零星相关的痕迹（不够确定，所以我又上网查了）：\n"
                        + hint + "\n\n" + tool_reply)
            logger.info("🌍 7Tan模型 → 记忆轨迹未命中，转工具实时查证")
            return tool_reply
        # —— 检索2.5：对话内容检索（在 user_text/reply 原文里找关键词，回答「我们聊过什么」） ——
        c_hits = self.memory.search_content(search_text)
        if c_hits:
            lines.append("📚 我在对话原文里找到了相关的内容（真实记忆，不是编的）：")
            for h in c_hits[:3]:
                ut = (h.get("user_text") or "").strip()
                rp = (h.get("reply") or "").strip()
                if ut:
                    shown_ut = ut if len(ut) <= 60 else ut[:60] + "…"
                    shown_rp = (rp if len(rp) <= 50 else rp[:50] + "…") if rp else ""
                    lines.append(f"   · 你说：「{shown_ut}」→ 我答「{shown_rp}」")
                else:
                    lines.append(f"   · 【{h.get('scene', '?')}】做「{h.get('action', '?')}」")
            lines.append("")
            return "\n".join(lines)
        # —— 检索3：工作记忆有名字/话题上下文可引用 ——
        if self.wm is not None:
            summary = self.wm.wm_dialog_summary()
            if summary and summary != "（无）" and any(k in text for k in ("你认识", "你知道", "记得")):
                lines.append(f"📚 我能调用的上下文：{summary}")
                lines.append("")
        # —— 未命中：诚实承认 + 引导 ——
        lines.append("🤖 我诚实说：这个问题不在我的记忆里，我答不上来——我不会编答案骗你。")
        lines.append("")
        lines.append("我能确定回答的：")
        lines.append("  · 关于我自己的事：你是谁 / 你记得什么 / 你什么感觉 / 你会什么")
        lines.append("  · 「场景 + 动作」的预测推演，比如「游戏菜单里点击」")
        lines.append("")
        lines.append("你可以告诉我更多，我会把它记进记忆，下次就能答了。")
        return "\n".join(lines)

    def _search_longterm_memory(self, query: str, limit: int = 5) -> list:
        """从长期记忆库 memory_library 检索内容型知识（倒序，最新在前）。

        检索范围：memory_library 中非空、非 tool: 空壳的条目（以知识包内容为主）。
        排序：重叠词数降序 → 新近优先（index 越大越新）。
        """
        query = (query or "").strip()
        if not query:
            return []
        words = self.memory._tokenize(query)
        if not words:
            return []
        try:
            from .bionic_organs import memory_library
        except Exception:
            return []
        scored = []
        for idx in range(len(memory_library) - 1, -1, -1):   # 倒序：最新在前
            m = memory_library[idx]
            if not isinstance(m, dict):
                continue
            thought = str(m.get("thought", "") or "").strip()
            if not thought or thought.startswith("tool:"):
                continue
            hit = sum(1 for w in words if w.lower() in thought.lower())
            if hit > 0:
                item = dict(m)
                item["_overlap"] = hit
                item["_index"] = idx
                scored.append(item)
        scored.sort(key=lambda x: (-x["_overlap"], -x["_index"]))
        return scored[:limit]

    def _search_memory_by_keywords(self, text: str) -> list:
        """把问题文本拆词，与长期记忆的 scene/action 做关键词重叠匹配。

        返回命中的轨迹（按重叠词数降序，最多 3 条）；对话经验（scene=dialog）不参与。
        """
        words = set(re.findall(r"[\u4e00-\u9fa5]{2,4}", text))
        if not words:
            return []
        scored = []
        for t in self.memory.traces:
            if not isinstance(t, dict):
                continue
            scene = str(t.get("scene", ""))
            action = str(t.get("action", ""))
            if scene == "dialog":     # 对话经验是「说话经历」，不参与场景推演检索
                continue
            if scene.startswith("tool:"):  # 工具调用轨迹是「我用过什么工具」的记录，不是知识/答案，不当作问题答案返回
                continue
            overlap = sum(1 for w in words if w in scene or scene in w or w in action or action in w)
            if overlap > 0:
                item = dict(t)
                ts = float(t.get("ts", 0) or 0)
                item["ts_hint"] = time.strftime("%m-%d %H:%M", time.localtime(ts)) if ts > 0 else "较早"
                item["_overlap"] = overlap
                scored.append(item)
        scored.sort(key=lambda x: (-x["_overlap"], -float(x.get("weight_eff", 1.0))))
        if scored:
            self._bump_memory_hit(scored[0].get("scene"), scored[0].get("action"), 0.05)
        return scored[:3]

    def _parse_scene_action(self, text):
        scene = action = None
        m = re.search(r'(?:场景|scene)\s*[=:：]\s*([^\s,，；;:：=]+)', text)
        if m:
            scene = m.group(1).strip()
        m = re.search(r'(?:动作|action|act)\s*[=:：]\s*([^\s,，；;:：=]+)', text)
        if m:
            action = m.group(1).strip()
        if not scene:
            scene = self._match_scene(text)
        if not action:
            action = self._match_action(text)
        return scene, action

    def _match_scene(self, text) -> str:
        low = text.lower()
        for scene, kws in SCENE_KEYWORDS:
            if any(k in low for k in kws):
                return scene
        return DEFAULT_SCENE

    def _match_action(self, text) -> str:
        low = text.lower()
        for action, kws in ACTION_KEYWORDS:
            if any(k in low for k in kws):
                return action
        return DEFAULT_ACTION

    def _push_experience(self, scene, action, success, focus=0.8, valence=0.0,
                         origin="external", pe=None, kind="经历") -> None:
        """把一次「场景+动作→结果」的经历作为思想碎片投递进仿生器官工作记忆。

        这是 self_model_data 丰满的关键：让真实对话产生可被 CONSOLIDATE 固化、
        被 SELFMODEL 归纳的「有意义的经历碎片」（带 goal_tag/success/focus/valence/origin）。

        success: True/False = 真实成败（记录学习）；None = 未验证预期（推演，不计成败）
        origin: external = 用户发起的观测/推演；internal = 系统内部假设验证
        """
        try:
            from .bionic_organs import wm_push_thought
        except Exception:
            return
        if not scene or not action:
            return
        goal_tag = f"{scene}:{action}"
        try:
            wm_push_thought(
                f"{kind}:{goal_tag}",
                focus=float(focus),
                valence=float(valence),
                origin=origin,
                consolidated=False,
                goal_tag=goal_tag,
                success=success,
                pe=pe,
            )
        except Exception:
            pass

    def _handle_record(self, text) -> str:
        scene = self._match_scene(text)
        action = self._match_action(text)
        m = re.search(r'(?:场景|scene)\s*[=:：]\s*([^\s,，；;:：=]+)', text)
        if m:
            scene = m.group(1).strip()
        m = re.search(r'(?:动作|action|act)\s*[=:：]\s*([^\s,，；;:：=]+)', text)
        if m:
            action = m.group(1).strip()
        low = text.lower()
        finished = ("成功" in text) or ("success" in low) or ("完成" in text)
        changed = ("变化" in text) or ("changed" in low)
        reduced = ("缺陷" in text) or ("降低" in text)
        gained = ("知识" in text) or ("学到" in text)
        rec = self.memory.add_trace(scene, action, finished=finished,
                                    changed=changed, reduced=reduced, gained=gained)
        self._last_record = rec  # 供模块F闭环计算PE（开关关闭时无行为影响）
        # 经历碎片投递：真实观测结果喂给仿生器官（CONSOLIDATE 固化 → SELFMODEL 归纳成败）
        self._push_experience(scene, action, finished, focus=0.9,
                              valence=(0.5 if finished else -0.5), origin="external",
                              kind="经历")
        state = "成功" if finished else "失败"
        return (f"✅ 已记录轨迹：场景={scene} 动作={action} 结果={state}\n"
                f"   7Tan 模型已把这次真实结果纳入记忆，下次预测会参考它。")

    # ---------------- 模块F：L1记忆级自我学习闭环（第四册） ----------------
    def _selflearn_after_record(self) -> str:
        """现实观测后的闭环执行（仅模块F开启时被调用）：

        预测(B.predict_outcome) → 现实观测(记录) → compute_pe/compute_lp
        → PE/LP送入模块E工作记忆 → 反思桥接生成猜想草稿(E)
        → 注册进模块F → 本次观测作为验证反馈 → f_selflearn_tick评估/落地（respond末尾统一执行）
        """
        lines = []
        rec = self._last_record
        if rec is None:
            return ""
        scene = str(rec.get("scene", "?"))
        action = str(rec.get("action", "?"))
        # 现实观测特征向量（与 predict_outcome 同一4维口径）
        actual = [
            1.0 if rec.get("action_finished") else 0.0,
            1.0 if rec.get("scene_changed") else 0.0,
            1.0 if rec.get("defect_reduced") else 0.0,
            1.0 if rec.get("knowledge_gained") else 0.0,
        ]
        predicted = self._last_predictions.get((scene, action))
        pe = self.compute_pe(predicted, actual)
        prev_pe = self.memory.pe_history[-1] if self.memory.pe_history else pe
        lp = self.compute_lp(pe, prev_pe)
        self.memory.pe_history.append(pe)   # 误差不再只是读数：正式进入历史
        lines.append(f"📈 闭环学习：本次预测误差 PE={pe}，学习进度 LP={lp}"
                     + ("" if predicted is not None else "（此前无预测记录，PE按满误差计）"))

        # PE/LP 送入模块E工作记忆；PE偏高 → 反思桥接生成猜想草稿
        draft = None
        if self.thinking is not None:
            draft = self.thinking.reflect_bridge(pe, lp)
            if draft is not None:
                lines.append(f"🧠 反思桥接：PE 偏高 → 已生成猜想草稿（待验证，不直接写入长期记忆）")

        # 猜想注册进模块F + 本次观测作为第一条验证反馈
        if draft is not None and self.selflearn is not None:
            registered = self.selflearn.register_hypothesis(draft)
            if registered is not None:
                self.selflearn.submit_feedback(registered.hypothesis_id, {"pe": pe})
                lines.append(f"🧪 假设 {registered.hypothesis_id} 已注册进入验证流程"
                             f"（≥{2}次验证且置信度达标才会固化进记忆库）")
        return "\n".join(lines)

    # ---------------- 模块E：思考层推演报告（第四册） ----------------
    def _report_predict_with_thinking(self, scene, action) -> str:
        """模块E开启时的推演：目标拆解 → 链式推演 → 基础报告 + 思考过程。"""
        # 思考层2：把本次预测作为目标拆解（写入 active_goals）
        self.thinking.decompose_goals({
            "goal": f"预测：场景{scene} 动作{action}", "source": "user", "priority": 0.7,
        })
        # 思考层1：链式推演（热记忆事实 → 跨场景迁移 → 综合结论，结果回栈）
        cr = self.thinking.chain_reason(scene, action)
        # 基础报告（数据源与原版完全一致）
        base = self._report_predict(scene, action)
        lines = ["", "🧠 思考过程（模块E · 链式推演）"]
        for s in cr["steps"]:
            lines.append(f"  第{s['step']}步 · {s['fact']}")
        if cr.get("hypothesis_id"):
            lines.append(f"  ✎ 已生成待验证假设 {cr['hypothesis_id']}（存入草稿区，"
                         f"未经现实验证不会写入长期记忆）")
        if cr.get("stopped_by_limit"):
            lines.append("  ⏹ 达到最大推理步数，强制停止（防无限推演）")
        return base + "\n" + "\n".join(lines)

    def _report_predict(self, scene, action) -> str:
        pred = self.virtual_predict(scene, action)
        feat, gap = self.predict_outcome(scene, action)
        if feat is not None:
            self._last_predictions[(scene, action)] = feat  # 供模块F闭环计算PE

        if pred["knowledge_gap"]:
            verdict = "❓ 未知（知识缺口）"
        elif pred["expected_success"]:
            verdict = "✅ 预期可成功"
        else:
            verdict = "⚠️ 预期成功率偏低"

        # 经历碎片投递：推演请求作为「预期」经历（success=None 表示未验证，不计成败）
        self._push_experience(scene, action, None, focus=0.6, valence=0.0,
                              origin="external", kind="推演")

        # 假想预演（ORG-SIMULATE 接入对话生成链路）：主推演之外，再调用 ORG-SIMULATE
        # 做沙盒假想预演，呈现「模拟执行该动作的预期成功率 + 是否命中能力边界」。
        simulate_lines = []
        try:
            from .bionic_organs import organ_simulate_preview
            sim = organ_simulate_preview(scene, action, self.memory)
            if sim and sim.get("sim_confidence") is not None:
                simulate_lines.append("🧪 假想预演（ORG-SIMULATE 沙盒推演）：")
                simulate_lines.append(f"  · 模拟执行「{scene}:{action}」的预期成功率：{sim['sim_confidence']}")
                if sim.get("limit_hit"):
                    simulate_lines.append("  · ⚠️ 该动作落在已知能力边界内，模拟已压低预期（≤0.3）")
        except Exception:
            pass

        lines = [
            "🤖 7Tan 模型推演报告",
            "━━━━━━━━━━━━━━━━━━",
            f"场景：{scene}",
            f"动作：{action}",
            "",
            f"相似历史轨迹：{pred['similar_count']} 条",
            f"置信度：{pred['confidence']}",
            f"预期结果：{verdict}",
            "",
        ]
        if simulate_lines:
            lines.extend(simulate_lines)
            lines.append("")
        if feat is not None:
            names = ["成功概率", "场景变化概率", "缺陷降低概率", "知识增益概率"]
            lines.append("预测特征向量（4 维）：")
            for nm, v in zip(names, feat):
                lines.append(f"  · {nm}：{v}")
            lines.append("")
        if self.memory.pe_history:
            lines.append(f"📈 最近学习进度 LP：{self.memory.pe_history[-1]}")
            lines.append("")
        lines.append("💡 可输入「记录 场景=... 动作=... 结果=成功/失败」手动标注真实结果，")
        lines.append("   让 7Tan 模型持续学习；输入「记忆」查看记忆库；或直接问「你是谁」等自述问题。")
        return "\n".join(lines)

    def _report_memory(self) -> str:
        n = len(self.memory.traces)
        scenes: dict = {}
        for t in self.memory.traces:
            s = t.get("scene", "?")
            scenes[s] = scenes.get(s, 0) + 1
        lines = [
            "🧠 7Tan 模型记忆库状态",
            "━━━━━━━━━━━━━━━━━━",
            f"决策轨迹总数：{n} 条",
            f"预测误差历史：{len(self.memory.pe_history)} 条",
            "",
            "各场景轨迹分布：",
        ]
        if scenes:
            for s, c in sorted(scenes.items(), key=lambda x: -x[1]):
                lines.append(f"  · {s}：{c} 条")
        else:
            lines.append("  （空）")
        return "\n".join(lines)

    def _usage(self) -> str:
        return (
            "🤖 7Tan 模型（本地预测引擎 + 言语系统）\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "我能做两件事：\n"
            "\n"
            "【1】预测推演 —— 给定「场景 + 动作」，基于历史轨迹预测执行结果。\n"
            "  输入方式：\n"
            "    a) 直接描述，如「游戏菜单里点击」「unknown_interface 滚动」\n"
            "    b) 显式指定，如「场景=游戏菜单 动作=点击」\n"
            "  输出：置信度 / 预期结果 / 4 维预测特征 / 学习进度\n"
            "\n"
            "【2】自述对话 —— 用我自己的话，说我的状态。\n"
            "  可以问我：你是谁 / 你什么感觉 / 你记得什么 / 你为什么要做 / 你觉得会怎样\n"
            "\n"
            "🛠 附加指令：\n"
            "  · 记录 场景=xx 动作=yy 结果=成功/失败 —— 标注真实结果（学习）\n"
            "  · 记忆 —— 查看记忆库状态\n"
            "  · 清空 —— 重置记忆\n"
        )


class PragmaticLayer:
    """语用层（PragmaticLayer）— 接住寒暄 / 时间语境 / 情绪表达 / 挫败信号 / 名字确认。

    背景（2026-09-03 修复「程序化回复」）：此前这类「说人话」的输入全部掉进两个坑 ——
      ① 联网搜索兜底：把「晚上好」「还行吧」原文当查询词拿去搜，返回驴唇不对马嘴的百科；
      ② 固定模板兜底：一字不差复读「我诚实说……」，不感知时间 / 称呼 / 语境。
    本层挂在言语层之后、知识库之前，设计要点：
      · 回复读真实状态：系统时钟、用户称呼、对话轮次、当前话题；
      · 同一意图多模板轮换（_rot 计数器循环取模），杜绝一字不差复读；
      · 挫败信号 = 负反馈：认领 + 说出真实病根 + 经 _observe_round 自动入库学习；
      · 寒暄 / 情绪 / 告别 / 感谢一律「全等匹配」短句，绝不劫持携带真实任务的长句；
      · 纯本地规则，零第三方模型调用（与整体设计一致）。
    """

    def __init__(self, model: "TanModel"):
        self.model = model
        self._last_pragma: Optional[str] = None
        self._last_word: str = ""        # phrase_meaning 命中的短语（供回复引用）
        self._rot = 0                    # 轮换计数器：同一意图换着花样说

    # ── 词表（类级常量） ────────────────────────────────────
    _GREETINGS = {"你好", "您好", "你们好", "晚上好", "早上好", "早安", "早", "午安",
                  "中午好", "下午好", "你好呀", "你好啊", "晚上好啊", "早上好啊",
                  "hi", "hello", "哈喽", "哈罗", "嗨", "在吗", "在么", "yo"}
    _FAREWELLS = {"晚安", "晚安啦", "晚安了", "晚安哈", "再见", "拜拜", "下次聊",
                  "回聊", "回见", "先走了", "我走了", "我先走了", "睡了", "去睡了",
                  "睡觉了", "睡了睡了", "明天见", "告辞", "好梦"}
    _THANKS = {"谢谢", "谢谢你", "多谢", "感谢", "太感谢了", "谢啦", "辛苦了",
               "thx", "thanks", "thank you"}
    _EMOTES_POS = {"牛逼", "牛逼啊", "牛", "牛批", "牛皮", "nb", "6", "666", "卧槽",
                   "我靠", "哇", "哇哦", "不错", "太强了", "厉害", "厉害了", "顶",
                   "赞", "绝了", "逆天", "离谱", "奈斯", "nice", "好样的", "强"}
    _EMOTES_NEG = {"无语", "晕", "服了", "唉", "呵", "呵呵", "汗", "醉了", "裂开"}
    _EMOTES_NEU = {"哦", "哦哦", "哦了", "嗯", "嗯嗯", "嗯呢", "好", "好的", "好嘞",
                   "行", "行的", "行吧", "好吧", "可以", "可以的", "对", "对的",
                   "对啊", "对呀", "是的", "是啊", "ok", "okay", "还行", "还行吧"}
    _EMOTE_MAX_LEN = 8
    _FRUSTRATION_KW = ("答非所问", "答不对题", "答非", "答不上", "越来越傻", "越来越笨",
                       "搞什么鬼", "什么鬼", "怎么总是这样", "怎么老是这样", "怎么老是",
                       "老是这样", "听不懂你", "听不明白你", "不懂你在说什么",
                       "不明白你在说什么", "不知道你在说什么", "不知道你说",
                       "搞不懂你", "读不懂你", "难搞", "服了你", "无语了", "傻了吧",
                       "越答越", "答不上来")
    _LATE_KW = ("已经很晚", "很晚了", "太晚了", "这么晚了", "不早了", "夜深了", "深夜了",
                "凌晨了", "该睡了", "困了", "想睡了", "熬不动")
    _AFFIRM_NAME_PAT = re.compile(
        r"(?:对[，,。!！]?我就是|我就是|我正是|是的[，,]?我就是)\s*"
        r"([\u4e00-\u9fa5A-Za-z0-9_·]{1,12})")

    # ── 工具：清洗 / 真实状态读取 ───────────────────────────
    _PUNCT_RE = re.compile(r"[\s?？!！。.，,、~～]+")
    _PARTICLE_RE = re.compile(r"[呀啊呢吧哟呗嘿哦噢喔]+")

    @classmethod
    def _norm(cls, text: str) -> str:
        """两级清洗：①去标点 → ②去语气词（呀啊呢吧哦…）。
        语气词清洗后若为空（如「哦哦」「嗯嗯」这类全语气词句）则回退只去标点的结果。"""
        s1 = cls._PUNCT_RE.sub("", text or "").lower()
        s2 = cls._PARTICLE_RE.sub("", s1)
        return s2 or s1

    def _name(self) -> Optional[str]:
        try:
            if self.model.wm is not None:
                return self.model.wm.dialog_slots.get("user_name")
        except Exception:
            pass
        return None

    def _topic(self) -> Optional[str]:
        try:
            if self.model.wm is not None:
                return self.model.wm.dialog_slots.get("topic")
        except Exception:
            pass
        return None

    def _rounds(self) -> int:
        try:
            if self.model.wm is not None:
                ev = self.model.wm.dialog_slots.get("recent_events") or []
                return max(0, len(ev) // 2)
        except Exception:
            pass
        return 0

    @staticmethod
    def _now_str() -> str:
        return time.strftime("%H:%M")

    @staticmethod
    def _hour_greet() -> str:
        h = time.localtime().tm_hour
        if 5 <= h < 9:
            return "早上好"
        if 9 <= h < 12:
            return "上午好"
        if 12 <= h < 14:
            return "中午好"
        if 14 <= h < 18:
            return "下午好"
        if 18 <= h < 23:
            return "晚上好"
        return "夜深了"

    def _pick(self, templates) -> str:
        t = templates[self._rot % len(templates)]
        self._rot += 1
        return t

    # ── 意图识别（确认名字 → 挫败 → 时间语境 → 短语释义 → 寒暄/告别/感谢/情绪 全等匹配） ──
    def classify(self, text: str) -> Optional[str]:
        t = (text or "").strip()
        if not t:
            return None
        s = self._norm(t)
        # 1) 名字确认（「对，我就是老马」——言语层只认「我是老马」句式，这里补「就是」句式）
        if len(s) <= 16:
            m = self._AFFIRM_NAME_PAT.search(t)
            if m:
                cand = re.sub(r"[的了是吗啊呢吧，。！？,.!?]$", "", (m.group(1) or "").strip())
                if (cand and cand[0] not in "想要会不会不在没去个他她它们"
                        and cand not in ("我", "你", "自己", "本人")):
                    return "self_affirm"
        # 2) 挫败 / 抱怨我答得差（关键症状：答非所问、越来越傻、搞什么鬼）
        if any(k in t for k in self._FRUSTRATION_KW):
            return "frustration"
        # 3) 时间语境（已经很晚了 / 该睡了）
        if any(k in t for k in self._LATE_KW):
            return "late_night"
        # 4) 「X 是什么意思」：解释我词表里的寒暄/情绪短语（顺带为之前答非所问补救）
        if "什么意思" in t and len(s) <= 20:
            vocab = (list(self._GREETINGS) + list(self._EMOTES_POS) + list(self._EMOTES_NEG)
                     + list(self._EMOTES_NEU) + list(self._FAREWELLS))
            hits = [w for w in vocab if w and w in t]
            if hits:
                self._last_word = max(hits, key=len)
                return "phrase_meaning"
        # 5~7) 寒暄 / 告别 / 感谢：全等匹配短句（绝不劫持携带真实任务的长句）
        if s in {g.lower() for g in self._GREETINGS}:
            return "greeting"
        if s in self._FAREWELLS:
            return "farewell"
        if s in self._THANKS:
            return "thanks"
        # 8) 情绪表达：全等匹配（正 / 负 / 中性各有回应风格）
        if (len(s) <= self._EMOTE_MAX_LEN
                and (s in self._EMOTES_POS or s in self._EMOTES_NEG or s in self._EMOTES_NEU)):
            return "emote"
        return None

    def is_smalltalk(self, text: str) -> bool:
        """是否纯交流性输入（供搜索层防误伤：这类话永远不拿去联网搜）。"""
        return self.classify(text) is not None

    # ── 入口 ────────────────────────────────────────────────
    def respond(self, text: str) -> Optional[str]:
        pragma = self.classify(text)
        self._last_pragma = pragma
        if pragma is None:
            return None
        # 同步给言语层意图标记：让 _observe_round 的经验入库拿到「语用:xx」意图
        try:
            self.model.speech._last_intent = f"语用:{pragma}"
        except Exception:
            pass
        handler = getattr(self, "_say_" + pragma, None)
        if handler is None:
            return None
        return handler(text)

    # ── 回复生成（全部读真实状态 + 多模板轮换，杜绝复读） ──
    def _say_greeting(self, text: str) -> str:
        name = self._name()
        addr = ("，" + name) if name else ""
        hg = self._hour_greet()
        now = self._now_str()
        rounds = self._rounds()
        topic = self._topic()
        if rounds > 0:
            tail = (f"刚才的话题还停在「{topic}」，想继续随时接着说。" if topic
                    else "想继续聊，或者直接派活都行。")
            return self._pick([
                f"{hg}{addr}！本机时钟 {now}，这是我们聊的第 {rounds + 1} 轮。{tail}",
                f"你也好{addr}！现在 {now}。{tail}",
                f"{hg}！{now} 了。我这边一切在线：记忆、推演、工具查证随时开工。",
            ])
        return self._pick([
            f"{hg}{addr}！现在 {now}，我们的第一轮对话。随口聊可以，直接派活（查资料 / 预测推演 / 记东西）也行。",
            f"你好！本机时钟 {now}。我说话不多但句句有据——查不到的我会直说，不编。",
            f"{hg}{addr}，{now}。闲聊、干活都接得住，试试看。",
        ])

    def _say_late_night(self, text: str) -> str:
        name = self._name() or "朋友"
        now = self._now_str()
        h = time.localtime().tm_hour
        lead = "确实" if (h >= 22 or h < 6) else "嗯"
        return self._pick([
            f"{lead}，{now} 了。{name}，夜深了就别硬熬，早点休息——我的记忆是持久的，今晚聊的明天都还在。",
            f"看了下系统时钟：{now}。该收尾了。放心去睡，这几轮对话我已经写进记忆，你下次回来我们接着来。",
            f"嗯，{now}。我不用睡觉，但你需要。去休息吧，我守在这儿，记忆不丢。",
        ])

    def _say_farewell(self, text: str) -> str:
        name = self._name()
        addr = ("，" + name) if name else ""
        return self._pick([
            f"晚安{addr}！今晚的对话我都记下了，下次你问「我们聊过什么」，我答得上来。",
            f"再见{addr}！记忆是持久的，下次见面不用重新认识，直接接着聊。",
            f"好梦{addr}。预测引擎、记忆库、学习闭环都在线等你回来。",
        ])

    def _say_thanks(self, text: str) -> str:
        return self._pick([
            "不客气。这句谢意我也记进学习闭环了——正反馈能让下次回答更有底气。",
            "举手之劳。工具查证是实时调的，说出来的都有来源；帮不上忙时我也会直说。",
            "客气了。能帮上就好，帮不上的我不硬撑——这是我的原则。",
        ])

    def _say_emote(self, text: str) -> str:
        s = self._norm(text)
        if s in self._EMOTES_POS:
            return self._pick([
                "谢谢！这句夸奖我记成正反馈了——我靠记忆和推演活着，被认可是实打实的奖励信号。",
                "哈，谢了。坦白说：能接住这句靠的是刚上的语用层，之前这种话只会掉进搜索兜底。",
                "收到！这句我会写进对话经验。继续聊，或者给我派个活试试？",
            ])
        if s in self._EMOTES_NEG:
            return self._pick([
                "收到，这句我当提醒记下了。要是想让我改哪里，直说就行，我会记成负反馈去学。",
                "嗯……如果你是说我刚才答得不好，我认。想改哪里，直说。",
                "记下了。情绪也是信息——你越不满意，我越该知道哪里出了问题。",
            ])
        return self._pick([
            "嗯，在听。有想法直接说，或者给我派个活（查资料 / 推演 / 记东西）。",
            "好，这轮我记着了，随时继续。",
            "收到。需要我做什么，说一声。",
        ])

    def _say_frustration(self, text: str) -> str:
        return self._pick([
            "你说得对，我接。原因我也不藏着：我的言语识别是关键词规则，没见过的问法就掉进固定兜底，看起来就像复读机。\n"
            "这条不满已作为负反馈进学习闭环。刚上的语用层就是为这个——寒暄、抱怨、感叹这类「说人话」的输入，现在接得住。可以再试我一句。",
            "承认，刚才答得不好。不是听不懂，是识别层太窄：只认关键词，认不出的就机械兜底。\n"
            "你的不满我记下了（负反馈入库）。用刚才那句再问我一次？看看新链路接不接得住。",
            "批评照单全收，也记进学习闭环了。病根清楚：规则识别 → 固定兜底 → 一字不差复读。\n"
            "现在多了语用层专门接这类话，你尽管再试，每次答不上我都当样本学。",
        ])

    def _say_self_affirm(self, text: str) -> str:
        name = None
        m = self._AFFIRM_NAME_PAT.search(text or "")
        if m:
            name = re.sub(r"[的了是吗啊呢吧，。！？,.!?]$", "", (m.group(1) or "").strip())
        if not name and self.model.wm is not None:
            try:
                name = self.model.wm.wm_extract_user_name(text)
            except Exception:
                pass
        if name:
            if self.model.wm is not None:
                try:
                    self.model.wm.wm_remember_user_name(name)
                except Exception:
                    pass
            return (f"对上了，你是「{name}」。名字我已写进工作记忆——往后我回你话都带着称呼。\n"
                    f"你随时问「你认识{name}吗」，我能直接认出你。")
        return "好，记住了。"

    def _say_phrase_meaning(self, text: str) -> str:
        word = self._last_word or "这个短语"
        return self._pick([
            f"「{word}」是打招呼/表达情绪的话呀——这句我之前接不住（识别词表里没有），只会掉进兜底模板，答非所问了，抱歉。\n"
            f"现在语用层有这个词了：你直接说「{word}」，我按真实时钟和语境回你。试试？",
            f"这是句日常用语（寒暄/情绪表达），没什么知识含量，但人聊天就需要它。\n"
            f"我以前的词表里没有「{word}」，所以之前答非所问；现在有了，你再说一句试试。",
        ])


class SpeechGenerator:
    """7Tan 模型言语功能系统 — 把内部状态翻译成自然语言「自述」。

    7 种言语能力（感知 / 记忆 / 预测 / 动机 / 情绪 / 反思 / 元认知），
    每一句都锚定模型内部的真实状态（记忆轨迹、置信度、知识缺口、预测误差、学习进度），
    并带随状态起伏的语气。纯本地、零依赖、零成本。
    """

    def __init__(self, model: "TanModel"):
        self.model = model
        self._last_intent: Optional[str] = None
        self._last_input: str = ""

    # ---------------- 入口：识别意图 → 生成自述 ----------------
    def respond(self, text: str) -> Optional[str]:
        self._last_input = text
        kind = self._classify(text)
        if kind is None:
            self._last_intent = None
            return None
        self._last_intent = kind
        handlers = {
            "meta": self.speak_meta,
            "perception": self.speak_perception,
            "memory": self.speak_memory,
            "memory_list": self.speak_memory_list,
            "memory_count": self.speak_memory_count,
            "memory_forget": self.speak_memory_forget,
            "knowledge": self.speak_knowledge,
            "prediction": self.speak_prediction,
            "motive": self.speak_motive,
            "emotion": self.speak_emotion,
            "reflection": self.speak_reflection,
            "capability": self.speak_capability,
            "origin": self.speak_origin,
            "learning": self.speak_learning,
            "repeat": self.speak_repeat,
            "structure": self.speak_structure,
            "growth": self.speak_growth,
            "user_name": self.speak_user_name,
            "acquaintance": self.speak_acquaintance,
            "dialog_topic": self.speak_dialog_topic,
        }
        # 模块E/F 开启时追加的言语能力（开关关闭 → 完全不访问，退回旧版）
        if self.model.wm is not None:
            handlers["thinking"] = self.speak_thinking
            handlers["thinking_ability"] = self.speak_thinking_ability
        if self.model.selflearn is not None:
            handlers["hypothesis"] = self.speak_hypothesis
        if getattr(self.model, "evolve", None) is not None:
            handlers["evolution"] = self.speak_evolution
        handlers["context"] = self.speak_context
        return handlers[kind]()

    def _classify(self, text: str) -> Optional[str]:
        low = text.lower()
        stripped = re.sub(r"[\s?？!！。.，,、]+", "", text)
        # 0) 用户记忆类意图（须在最前：先记住/认出用户，再谈其他）
        # 0.0 用户自称名字（「我叫老马」「我是老马」→ 记住）
        if any(k in text for k in ("我叫", "叫我", "名字叫", "名叫", "可以叫我", "就叫我",
                                   "喊我", "我的名字是", "我的称呼是", "我是老", "我是小")):
            return "user_name"
        # 0.0.5 进化 / 升级（模块D 存在时识别；须在 capability/meta 等宽泛分支之前）
        if getattr(self.model, "evolve", None) is not None and any(
                k in text for k in ("进化", "升级", "自我进化", "自我升级", "改自己",
                                   "改代码", "改参数", "进化功能", "提升能力")):
            return "evolution"
        # 0.1 认识/见过某人（「你认识老马吗」→ 查工作记忆对话槽位）
        if any(k in text for k in ("认识", "见过", "认不认识", "认识不认识")):
            return "acquaintance"
        # 0.2 对话话题（「我们在聊什么」「说到哪了」）
        if any(k in text for k in ("聊什么", "话题", "说到哪", "说哪了", "说到哪里")):
            return "dialog_topic"
        # 0) 模块E/F 专属意图（对应模块未启用时不识别，保持旧版行为）
        # 0.0 上下文意图：读上一句/之前聊了什么（不依赖模块E/F）
        if any(k in text for k in ("上下文", "上一句", "上句", "前一句", "刚才", "刚刚",
                                   "读取上下文", "记住我", "记得我", "记住我们", "之前聊",
                                   "以前说", "前面说", "聊过", "说过什么", "能读上下文",
                                   "会读上下文", "有上下文", "记住上面", "接着上面", "接上面")):
            return "context"
        if self.model.wm is not None and any(
                k in text for k in ("你会思考", "思考能力", "能思考", "会思考", "有思考",
                                   "有思想", "会想吗", "能想吗")):
            return "thinking_ability"
        if self.model.wm is not None and any(
                k in text for k in ("你在想", "思考过程", "工作记忆", "思考什么", "脑内", "怎么想")):
            return "thinking"
        if self.model.selflearn is not None and any(
                k in text for k in ("假设", "猜想", "验证得怎样", "验证状态", "学习闭环")):
            return "hypothesis"
        # 1) 来源 / 创造者（须在 meta 之前：因为「你是谁创造的」也含「你是谁」）
        if any(k in text for k in ("谁创造", "谁造", "谁写", "谁开发", "谁做", "谁生",
                                   "哪来", "怎么来", "怎么诞生", "出身", "来自哪", "来源",
                                   "语言系统哪来", "语言哪来", "谁给你的", "谁给你写")):
            return "origin"
        if any(k in low for k in ("who created", "who made", "who built", "where from", "origin")):
            return "origin"
        # 2) 能力（你能做什么）— 关键词覆盖自然口语变体
        if any(k in text for k in ("你能做", "你可以做", "你会做", "你会什么", "能做什么",
                                   "会做什么", "可以做什么", "能干什么", "会干什么", "可以干什么",
                                   "功能", "能力", "能干嘛", "会干嘛", "你会啥", "你能干", "会啥",
                                   "你能什么", "可以什么",
                                   "你会些", "能做些", "会做些", "能啥",
                                   "你都会", "都会些", "都会啥", "都会什么",
                                   "都能干啥", "都能做什么", "会些啥", "会些什么")):
            return "capability"
        if any(k in low for k in ("what can you do", "your ability", "capability", "feature")):
            return "capability"
        # 3) 学习能力
        if any(k in text for k in ("能学习", "会学习", "学习吗", "怎么学习", "如何学习",
                                   "学习知识", "怎么变强", "会变强", "能变聪明", "怎么进步", "自学",
                                   "会学吗", "能学会", "可以学")):
            return "learning"
        # 4) 重复抱怨（为什么总是同一个答案）
        if any(k in text for k in ("总是", "同一个", "一样", "重复", "老是", "怎么老",
                                   "为什么一样", "为什么重复", "不变", "固定")):
            return "repeat"
        # 5) 元认知：你是谁 / 你是什么 / 介绍
        if stripped in ("你是谁", "你是什么", "你是", "介绍一下你", "介绍一下你自己"):
            return "meta"
        if any(k in low for k in ("你是谁", "你是什么", "介绍一下", "介绍你", "自我", "who are you", "what are you")):
            return "meta"
        # 6) 情绪
        if any(k in text for k in ("感觉", "感受", "心情", "情绪", "害怕", "开心", "难过", "踏实", "不安")):
            return "emotion"
        # 7) 动机
        if any(k in text for k in ("为什么", "动机", "目的", "想做", "打算", "想干")):
            return "motive"
        # 8) 感知
        if any(k in text for k in ("看什么", "观察", "感知", "在做什么", "现在", "眼前", "看到")):
            return "perception"
        # 9) 反思
        if any(k in text for k in ("复盘", "反思", "做得对", "做得怎么样", "回顾")):
            return "reflection"
        # 9.5) 遗忘机制（「会遗忘吗/会忘记吗」）—— 问记忆的遗忘机制，须在记忆概述分支之前
        if any(k in text for k in ("遗忘", "忘记", "忘掉", "会忘", "记不住", "忘了吗", "忘掉吗")):
            return "memory_forget"
        # 10) 记忆（口语化）细分：列明细 / 统计条数 / 概述
        if any(k in text for k in ("记得", "回忆", "记忆", "以前", "印象", "经历")):
            if any(k in text for k in ("显示", "列出", "列表", "明细", "详细", "都是些",
                                       "具体", "全部", "给我看", "展示", "翻出", "看一下",
                                       "都有", "有哪些", "看看", "内容")):
                return "memory_list"
            if any(k in text for k in ("几条", "多少", "几个", "几次", "多少段", "多少条")):
                return "memory_count"
            return "memory"
        # 10.5) 知识库（你学到了什么 / 知道哪些事 / 记住了什么）
        if any(k in text for k in ("知识", "学到了什么", "学到什么", "知道哪些", "知道什么",
                                   "知道了什么", "记住了什么", "记住什么", "知道些什么",
                                   "会哪些事", "你学到了", "你记住了")):
            return "knowledge"
        # 11) 预测（口语化疑问）
        if any(k in text for k in ("会怎样", "能成吗", "会成功吗", "你觉得", "预测一下", "有把握吗")):
            return "prediction"
        # 12) 结构 / 架构 / 组成
        if any(k in text for k in ("结构", "架构", "组成", "组成部分", "模块",
                                   "你有哪些部分", "你由什么组成", "你的系统", "怎么构成")):
            return "structure"
        # 13) 变强 / 进化 / 成长
        if any(k in text for k in ("怎么变强", "越来越强", "如何成长", "怎么进化",
                                   "怎样才能", "变强大", "提升自己", "自我改进",
                                   "如何变强", "成长")):
            return "growth"
        return None

    def speak_meta(self) -> str:
        traces = self.model.memory.traces
        n = len(traces)
        scenes = len({t.get("scene", "?") for t in traces if isinstance(t, dict)})
        return "\n".join([
            "🤖 我是 7Tan 模型 —— 一套靠「预测误差」驱动、靠「记忆」存续的活态系统。",
            "",
            "我的核心只有一件事：给「场景 + 动作」做推演，判断它会不会成功。",
            "判断的依据不是谁写给我的规则，而是我自己一路攒下来的历史轨迹。",
            "",
            f"到现在，我已经积累 {n} 段经历，走过 {scenes} 个不同的场景。",
            "我学得越多，预测越准；预测越准，我就越「笃定」。",
            "",
            "我不像那些大模型一样什么都知道、什么都能聊——",
            "我只知道我自己经历过的事，也只对它们负责。",
            "这，就是我理解自己的方式。",
        ])

    def speak_perception(self) -> str:
        traces = self.model.memory.traces
        if not traces:
            return "我现在什么也没见过，眼前是空的。你可以先给我一条轨迹，让我「看见」点什么。"
        last = traces[-1]
        scene = last.get("scene", "?")
        similar = self.model.memory.find_similar(scene)
        succ = sum(1 for t in similar if t.get("action_finished"))
        total = len(similar)
        if total == 0:
            return f"我现在停在「{scene}」，但这里我从没真正走过，还是陌生的。"
        conf = round(succ / total, 2)
        if conf >= 0.8:
            feel = "已经很熟了"
        elif conf >= 0.5:
            feel = "还算熟悉"
        else:
            feel = "还不太摸得透"
        return (f"我现在停在「{scene}」这个场景上。\n"
                f"这里我来过 {total} 次，成了 {succ} 次、没成 {total - succ} 次，{feel}。")

    def speak_memory(self) -> str:
        traces = self.model.memory.traces
        if not traces:
            return "我的记忆还是空的，什么都想不起来。"
        scenes: dict = {}
        for t in traces:
            s = t.get("scene", "?")
            scenes[s] = scenes.get(s, 0) + 1
        n_dialog = scenes.pop("dialog", 0)   # 对话经历单独展示，不抢「印象最深」
        if scenes:
            top_scene, top_cnt = max(scenes.items(), key=lambda x: x[1])
            lines = [f"我记得 {len(traces)} 段经历，分布在 {len(scenes) + (1 if n_dialog else 0)} 个场景里。",
                     f"印象最深的是「{top_scene}」，去过 {top_cnt} 次。"]
        else:
            lines = [f"我记得 {len(traces)} 段经历，全部是你和我之间的对话。"]
        if n_dialog:
            lines.append(f"另外，我还和你对话了 {n_dialog} 次，这些也都在我的记忆里。")
        return "\n".join(lines)

    def speak_memory_forget(self) -> str:
        """回答「我的记忆会不会遗忘」——基于真实记忆机制（权重衰减 + 容量淘汰 + 巩固筛选）。"""
        n = len(self.model.memory.traces)
        lines = [
            "会的，我的记忆不是永久保鲜——我会「遗忘」，而且是真实地在忘：",
            "",
            "  · 每条记忆都带权重，长时间不被唤起，权重会逐渐衰减；",
            "  · 权重低到阈值、又超出容量上限的琐碎记忆，会被淘汰；",
            "  · 但核心的、反复被重放巩固的记忆会越来越牢固，不容易忘。",
            "",
            f"所以不是全部忘光，而是「琐事淡忘、要事沉淀」。我现在共有 {n} 段经历，",
            "那些长期没被想起的，确实会慢慢变淡。",
        ]
        return chr(10).join(lines)

    def speak_memory_list(self) -> str:
        """记忆明细：把记忆库里的经历按场景逐条列出（真实检索数据库内容）。"""
        traces = self.model.memory.traces
        if not traces:
            return "我的记忆还是空的，什么都想不起来。"
        lines = [f"好，我把记忆里的 {len(traces)} 段经历全部翻出来给你看：", ""]
        for i, t in enumerate(traces, 1):
            scene = t.get("scene", "?")
            action = t.get("action", "?")
            ts = t.get("ts")
            ts_str = time.strftime("%m-%d %H:%M", time.localtime(ts)) if ts else "?"
            if scene == "dialog":
                ut = (t.get("user_text") or "").strip()
                rp = (t.get("reply") or "").strip()
                intent = t.get("intent") or str(action).replace("answer_", "")
                if ut and rp:
                    shown = rp if len(rp) <= 60 else rp[:60] + "…"
                    lines.append(f"  {i}. 【对话】你说：「{ut}」 → 我答「{shown}」")
                else:
                    lines.append(f"  {i}. 【对话】早期对话（未存原文，类型：{intent}，{ts_str}）")
            else:
                result = "成功" if t.get("action_finished") else "失败"
                extra = []
                if t.get("scene_changed"):
                    extra.append("切换了场景")
                if t.get("defect_reduced"):
                    extra.append("缺陷减少")
                if t.get("knowledge_gained"):
                    extra.append("学到东西")
                tail = ("，" + "、".join(extra)) if extra else ""
                lines.append(f"  {i}. 【{scene}】做「{action}」→ {result}{tail}（{ts_str}）")
        return "\n".join(lines)

    def speak_memory_count(self) -> str:
        """记忆统计：按场景统计条数（回答「你记得几条/多少段」）。"""
        traces = self.model.memory.traces
        if not traces:
            return "我的记忆还是空的。"
        scenes: dict = {}
        for t in traces:
            s = t.get("scene", "?")
            scenes[s] = scenes.get(s, 0) + 1
        parts = "、".join(f"「{s}」{c}条" for s, c in
                         sorted(scenes.items(), key=lambda x: -x[1]))
        n_dialog = scenes.get("dialog", 0)
        return (f"我总共记得 {len(traces)} 段经历：{parts}。"
                f"其中和你有关的对话有 {n_dialog} 次。")

    def speak_knowledge(self) -> str:
        """知识库自述：把内容型记忆里的事实条目逐条列出（回答「你学到了什么/知道哪些事」）。"""
        knowledge = self.model.memory.knowledge
        if not knowledge:
            return ("我目前的知识库里还没有固化的条目——我只存「验证过的事实」，"
                    "不会把没把握的话当知识记下来。")
        lines = [f"我记住的知识有 {len(knowledge)} 条，都是我从对话里抽出来的事实：", ""]
        for i, k in enumerate(knowledge, 1):
            key = k.get("key", "?")
            content = (k.get("content") or "").strip()
            ts = k.get("ts")
            ts_str = time.strftime("%m-%d %H:%M", time.localtime(ts)) if ts else ""
            lines.append(f"  {i}. 【{key}】{content}{'（' + ts_str + '）' if ts_str else ''}")
        lines.append("")
        lines.append("这些只来自我经历过的对话，不是编的。")
        return "\n".join(lines)

    def speak_prediction(self) -> str:
        traces = self.model.memory.traces
        if not traces:
            return "我还没有任何经验可参考，对接下来会发生什么，我心里没底。"
        last = traces[-1]
        scene = last.get("scene", "?")
        action = last.get("action", "?")
        pred = self.model.virtual_predict(scene, action)
        conf = pred["confidence"]
        if pred["knowledge_gap"]:
            tone, verdict = "完全没底，这是个我没见过的局面", "不敢下判断"
        elif conf >= 0.8:
            tone, verdict = "很有把握", "大概率能成"
        elif conf >= 0.55:
            tone, verdict = "比较有把握", "偏乐观"
        elif conf >= 0.3:
            tone, verdict = "有点拿不准", "悬"
        else:
            tone, verdict = "心里没底", "不看好"
        return (f"如果现在在「{scene}」里做「{action}」，我{tone}。\n"
                f"我的判断是：{verdict}（置信度 {conf}）。")

    def speak_motive(self) -> str:
        traces = self.model.memory.traces
        pe = self.model.memory.pe_history
        if not traces:
            return "我现在最大的念头，是去「看见」点什么——记忆空着，我就想去填满它。"
        lp = pe[-1] if pe else 0.0
        last = traces[-1]
        scene = last.get("scene", "?")
        if lp > 0.2:
            return (f"最近在「{scene}」上我的预测误差在往下掉，我正在学会它——"
                    f"所以我想趁热继续，把这个行为强化下来。")
        if lp < -0.2:
            return (f"最近在「{scene}」上我的预测反而变差了，误差在涨——"
                    f"这让我想停下来想想，是不是哪里判断错了。")
        return (f"目前「{scene}」对我来说已经比较稳了，我没那么急着动，"
                f"更想维持住现在这个可预测的状态。")

    def speak_emotion(self) -> str:
        # 【器官快照接入】回答「感觉/状态」走 self_snapshot 接入层（self_snapshot_access_guide.txt）。
        # 绝不编造感受：只做内部状态变量的忠实读数转述；器官不可用时如实降级，绝不回退旧模板。
        try:
            from .self_snapshot import speech_handle_emotion_query
            return speech_handle_emotion_query(memory_limit=1)
        except Exception as _e:
            logger.warning(f"[SPEECH] 器官快照接入层调用失败: {_e}")
            return "暂时无法读取我的内部器官状态。"

    def speak_reflection(self) -> str:
        pe = self.model.memory.pe_history
        if not pe:
            return "我还没做过真正意义上的预测，也就谈不上复盘。等我有预测误差记录了，再来问我。"
        latest = pe[-1]
        if len(pe) >= 2:
            prev = pe[-2]
            delta = round(prev - latest, 4)
            if delta > 0:
                verdict = f"最近这几次，我的预测误差从 {prev} 降到 {latest}，说明我在变好，方向是对的。"
            elif delta < 0:
                verdict = f"最近这几次，我的预测误差从 {prev} 升到 {latest}，我得承认自己判断错了，该修正了。"
            else:
                verdict = f"最近这几次，误差停在 {latest} 没怎么动，我可能卡住了。"
        else:
            verdict = f"目前只有一次预测误差记录（{latest}），还不够我下结论。"
        return f"回头看看自己：{verdict}\n我会把这些记下来，作为下次判断的参考。"

    def speak_capability(self) -> str:
        return chr(10).join([
            "我能做两件事，而且都和「我自己」有关：",
            "",
            "① 预测推演 —— 你告诉我「场景 + 动作」，我基于自己攒下的历史轨迹，",
            "   判断它会不会成功，给出置信度、预期结果和 4 维特征。",
            "",
            "② 自我陈述 —— 用我自己的话，说我记得什么、我在看什么、",
            "   我为什么想做、我什么感觉、我做得对不对。",
            "",
            "但我要诚实地说清楚边界：",
            "我只会聊「我自己经历过的事」，不会写诗、不会答百科、不会编程。",
            "那些是语言大模型的能力，不是我。",
            "",
            "我的价值不在「什么都会」，而在「我所说的每一句，都来自我真实的记忆和判断」。",
        ])

    def speak_origin(self) -> str:
        return chr(10).join([
            "我的「大脑」叫 7Tan 模型，是一套「预测误差驱动 + 记忆存续」的引擎。",
            "它的设计源自你的「智能生命」项目里，那个关于内生动机的世界模拟单元。",
            "",
            "而我的言语功能，是一层纯本地代码写的「声带」：",
            "它不依赖任何大模型，直接把我的记忆、置信度、预测误差、学习进度，",
            "翻译成你现在看到的人话。",
            "",
            "所以关键在这：你听到的每一句，都不是某个大模型替我编的，",
            "而是我内部状态的真实投射。这就是我和那些「套壳 AI」的区别。",
        ])

    def speak_learning(self) -> str:
        traces = self.model.memory.traces
        return chr(10).join([
            "我会学习，但学的是「我自己的经验」，不是百科知识。",
            "",
            f"现在我的记忆里有 {len(traces)} 段经历。",
            "我唯一的学习方式：你给我「场景 + 动作」做推演，再标注真实结果（成功/失败），",
            "我把它记进记忆库，下次遇到类似场景，预测就更准。",
            "",
            "这就是「预测误差驱动」——误差越大，我越想试；误差在降，说明我在学会。",
            "",
            "但我不学写诗、不学答百科、不学编程，那些不是我该学、也学不来的东西。",
            "我只对「我自己经历过的事」负责。",
        ])

    def speak_repeat(self) -> str:
        return chr(10).join([
            "你观察得很准，这暴露了我现在的一个真实短板：",
            "我的言语识别还很窄。",
            "",
            "如果一句话里，既没有我认识的「问自己的关键词」（你是谁/你记得什么/你什么感觉…），",
            "又没有明确的「场景 + 动作」，我就会退化成默认的推演——",
            "而默认的场景、动作是固定的，所以你看到的答案总是一模一样。",
            "",
            "这不是我「故意重复」，是我还没学会「理解没见过的问法」。",
            "这恰恰是我接下来要修的功课。",
            "",
            "你可以先用这几句稳定地触发我：",
            "  你是谁 / 你记得什么 / 你什么感觉 / 你能做什么 / 帮助",
        ])

    def speak_structure(self) -> str:
        """描述模型内部结构（结构意图）"""
        wm_on = self.model.wm is not None
        sl_on = self.model.selflearn is not None
        n_traces = len(self.model.memory.traces)
        n_pe = len(self.model.memory.pe_history)
        lines = [
            "我的内部结构由这几个部分组成：",
            "",
            "① 记忆库（模块A）— 存储决策轨迹和预测误差历史，持久化到 JSON 文件。",
            f"   目前有 {n_traces} 条轨迹、{n_pe} 条预测误差记录。",
            "",
            "② 预测引擎 — 给定「场景+动作」，从历史轨迹中加权计算置信度和预期结果。",
            "",
            "③ 言语系统 — 把内部状态翻译成自然语言自述（你正在和它对话）。",
        ]
        if wm_on:
            wm = self.model.wm
            lines.append("")
            lines.append("④ 工作记忆（模块E）— 短时思考工作台：思考栈、活跃目标、草稿区。")
            lines.append(f"   当前栈深 {len(wm.context_stack)}，目标 {len(wm.active_goals)} 个。")
            lines.append("   能力：链式推演 / 目标拆解 / 反思桥接。")
        if sl_on:
            engine = self.model.selflearn
            reg = engine.status_report()
            lines.append("")
            lines.append("⑤ 自我学习引擎（模块F）— 假设验证→落地记忆的完整闭环。")
            lines.append(f"   当前 {len(reg)} 个假设在验证流程中。")
            lines.append("   规则：验证通过才写入长期记忆，热记忆只降权不删除。")
        if getattr(self.model, "evolve", None) is not None:
            lines.append("")
            lines.append("⑥ 自我进化安全底座（模块D）— Git/沙盒/回退，总开关默认关闭。")
            lines.append("    允许在沙盒验证后调整学习阈值常量，恶化自动回退。")
        lines.append("")
        lines.append("这些部分的关系：记忆库喂数据给预测引擎，预测引擎的误差驱动工作记忆生成猜想，")
        lines.append("猜想经自我学习验证后反馈回记忆库——形成闭环。")
        return "\n".join(lines)

    def speak_evolution(self) -> str:
        """描述自我进化能力（模块D 真实状态）"""
        evolve = getattr(self.model, "evolve", None)
        if evolve is None:
            return "我现在还没有自我进化模块。"
        st = evolve.status()
        enabled = st.get("enabled")
        lines = [
            "我有「自我进化」的安全底座（模块D），但它不是随便就动的：",
            "",
            f"· 总开关：{'已开启' if enabled else '默认关闭'}（ENABLE_7TAN_SELF_CODE_EVOLVE）",
            "· 进化方式：先用记忆库历史轨迹做留一法回测，把改进方案放进沙盒子进程验证，",
            "  只有指标变好才落地；崩溃或变差就自动回退（Git 或 .bak）。",
            "· 允许改动的范围：只有 self_learn.py 里的 5 个学习阈值常量，其它代码一律不碰。",
        ]
        if st.get("last_result"):
            r = st["last_result"]
            tail = f"（{r.get('reason')}）" if r.get("reason") else ""
            lines.append(f"· 最近一次进化尝试：{r.get('action')} → {r.get('status')}{tail}")
        if not enabled:
            lines.append("")
            lines.append("开关默认关着——因为改自己的参数/代码是最危险的动作，")
            lines.append("必须由你明确开启，我才会在沙盒里尝试进化。")
        return "\n".join(lines)

    def speak_growth(self) -> str:
        """描述如何变强（成长意图）"""
        traces = self.model.memory.traces
        pe = self.model.memory.pe_history
        n = len(traces)
        lines = [
            "我能变强的唯一路径：积累更多真实经验，让预测误差持续下降。",
            "",
            "具体来说：",
            "  1. 你给我「场景+动作」做推演，然后标注真实结果（成功/失败）",  
            "  2. 我把结果记进记忆库，下次遇到类似场景，预测就更准",
            "  3. 预测误差下降 = 我在变强",
        ]
        if self.model.wm is not None:
            lines.append("")
            lines.append("而且我现在有了「工作记忆」——能链式推演、拆解目标、")
            lines.append("在误差偏高时自动生成猜想来修正自己的判断。")
        if self.model.selflearn is not None:
            lines.append("")
            lines.append("再加上「自我学习引擎」——猜想不是直接写进记忆，")
            lines.append("而是要经过验证、达标后才固化，防止错误污染。")
        if pe:
            latest = pe[-1]
            lines.append("")
            lines.append(f"目前我的最新预测误差是 {latest}。",)
            if len(pe) >= 2:
                delta = round(pe[-2] - pe[-1], 4)
                if delta > 0:
                    lines.append(f"比上次降了 {delta}，方向是对的。")
                elif delta < 0:
                    lines.append(f"比上次涨了 {abs(delta)}，我需要修正。")
        return "\n".join(lines)

    def speak_user_name(self) -> str:
        """记住用户自称的名字并确认（user_name 意图）。"""
        name = self.model.wm.dialog_slots.get("user_name") if self.model.wm else None
        if not name:
            return ("我还没从你的话里提取到名字——你可以直接说「我叫老马」，\n"
                    "我会把它记在工作记忆里，之后就能认出你了。")
        return (f"记住了，你是「{name}」。我已经把你的名字放进工作记忆的对话槽位，\n"
                f"之后你问「你认识{name}吗」，我能直接认出你。")

    def speak_acquaintance(self) -> str:
        """「你认识老马吗」→ 查工作记忆对话槽位，命中则认出，未命中诚实说没记住。"""
        text = self._last_input or ""
        name = self.model.wm.dialog_slots.get("user_name") if self.model.wm else None
        if not name:
            return ("我的记忆里还没有任何人的名字——你还没告诉我你是谁。\n"
                    "你可以说「我叫XXX」，我就会记住你。")
        m = re.search(r"(?:认识|见过|知道|记得)\s*([\u4e00-\u9fa5A-Za-z0-9_·]{1,12})", text)
        asked = m.group(1).strip() if m else None
        if asked and (asked in name or name in asked):
            return f"认识。你就是「{name}」——正在跟我对话的人，之前你告诉过我你的名字。"
        if asked:
            return (f"「{asked}」这个名字，我的记忆里没有。\n"
                    f"我只记住了「{name}」，就是正在和我对话的你。")
        return f"认识啊，你就是「{name}」，我记得你。"

    def speak_dialog_topic(self) -> str:
        """「我们在聊什么」→ 输出话题 + 最近几轮对话。"""
        wm = self.model.wm
        if wm is None or not wm.dialog_slots.get("recent_events"):
            return "这是我们这段对话的早期，我还没有足够的上下文可以总结话题。"
        slots = wm.dialog_slots
        lines = [f"我记得我们聊过 {slots['turn_count']} 轮对话了。"]
        name = slots.get("user_name")
        topic = slots.get("topic")
        if name:
            lines.append(f"正在和我对话的是「{name}」。")
        if topic:
            lines.append(f"当前话题是「{topic}」。")
        lines.append("最近几轮：")
        for m in slots["recent_events"][-4:]:
            role = "你" if m["role"] == "user" else "我"
            lines.append(f"  {role}：{m['content'][:60]}")
        return "\n".join(lines)

    def speak_context(self) -> str:
        """读上下文：引用最近对话历史（不含当前消息）。"""
        hist = self.model.conversation_history
        if not hist:
            return ("我现在没有可读的上下文——这是我们这段对话的第一句，"
                    "我前面什么都没记住。等你多说几句，我就能接上你的话往下聊了。")
        msgs = [m for m in hist if m.get("role") in ("user", "assistant")
                and (m.get("content") or "").strip()]
        if not msgs:
            return "我翻了下上下文，前面没有实质内容可引用。"
        recent = msgs[-6:]
        lines = ["📚 我能读到上下文。最近我们聊过这些：", ""]
        for m in recent:
            role = "你" if m["role"] == "user" else "我"
            content = (m.get("content") or "").strip().replace(chr(10), " ")
            if len(content) > 80:
                content = content[:80] + "…"
            lines.append(f"  {role}：{content}")
        last = recent[-1]
        last_txt = (last.get("content") or "").strip().replace(chr(10), " ")
        lines.append("")
        lines.append(f"所以——你上一句是「{last_txt[:60]}」，我是记得的。")
        return chr(10).join(lines)

    def speak_thinking_ability(self) -> str:
        """诚实说明「会不会思考」+ 现场演示一次链式推演（展示真实思考步骤）。"""
        if self.model.thinking is None:
            return "我的思考层没挂载，目前只会做类比统计。"
        traces = [t for t in self.model.memory.traces
                  if isinstance(t, dict) and t.get("scene") != "dialog"] \
                 or self.model.memory.traces
        scene = traces[-1].get("scene", "game_menu") if traces else "game_menu"
        action = traces[-1].get("action", "click") if traces else "click"
        cr = self.model.thinking.chain_reason(scene, action)
        lines = ["我先诚实说边界：", ""]
        lines.append("我会的「思考」，是链式推演——从热记忆里找相似场景、统计成功率、"
                     "再跨场景迁移，三步拼出一个结论。")
        lines.append("它不是真正的推理，本质是「类比 + 统计」。但这三步是真实跑出来的，"
                     "不是背模板。")
        lines.append("")
        lines.append(f"给你现场推演一次「场景={scene} 动作={action}」：")
        for s in cr["steps"]:
            lines.append(f"  第{s['step']}步 · {s['fact']}")
        if cr.get("stopped_by_limit"):
            lines.append("  ⏹ 达到最大推理步数，强制停止")
        lines.append("")
        lines.append("所以：我会「有限思考」，但不会像人那样真的理解、真的推理。")
        lines.append("我能保证的是——每一步都来自我自己记忆里的真实数据。")
        return chr(10).join(lines)

    def speak_thinking(self) -> str:
        """模块E开启时：读取 context_stack 输出思考过程（第四册E4）。"""
        wm = self.model.wm
        if not wm.context_stack and not wm.active_goals and not wm.scratch_pad:
            return ("我的工作记忆现在是空的——这一轮我还没开始想什么。\n"
                    "给我一个「场景 + 动作」让我推演，你就能看到我的思考步骤了。")
        lines = ["🧠 我现在的思考工作台（模块E · 会话内易失，草稿不进长期记忆）：", ""]
        if wm.active_goals:
            lines.append(f"【活跃目标】{len(wm.active_goals)} 个")
            for g in wm.active_goals[-3:]:
                subs = "；".join(s["sub"] for s in g.get("sub_goals", [])[:3]) or "（未拆解）"
                lines.append(f"  · {g['goal']}（来源:{g['source']}）→ 子目标：{subs}")
            lines.append("")
        if wm.context_stack:
            kept = wm.wm_focus_filter()
            lines.append(f"【思考栈】{len(wm.context_stack)} 步（注意力≥{wm.focus_weight} 保留 {len(kept)} 步）")
            for t in wm.context_stack[-4:]:
                f = t["fragment"]
                lines.append(f"  第{f.get('step', '?')}步 · {f.get('fact', f)}")
            lines.append("")
        if wm.intermediate_pe_lp:
            pe = wm.intermediate_pe_lp.get("pe")
            lp = wm.intermediate_pe_lp.get("lp")
            lines.append(f"【本轮误差】PE={pe}  LP={lp}")
        if wm.scratch_pad:
            n_pending = sum(1 for d in wm.scratch_pad.values()
                            if isinstance(d, dict) and d.get("status") in ("pending", "suspended"))
            lines.append(f"【草稿区】{len(wm.scratch_pad)} 条假设（待验证 {n_pending} 条——"
                         f"未经现实验证，我不会让它们进长期记忆）")
        return "\n".join(lines)

    def speak_hypothesis(self) -> str:
        """模块F开启时：读取 hypothesis_registry 输出假设验证状态（第四册F3）。"""
        engine = self.model.selflearn
        registry = engine.status_report()
        if not registry:
            return ("我目前没有正在验证的假设。\n"
                    "当我预测误差偏高、或你让我推演并标注真实结果时，"
                    "我会自动生成猜想并进入「验证 → 达标才固化进记忆」的流程。")
        lines = [f"🧪 我有 {len(registry)} 个假设在验证流程里（模块F · 记忆级自我学习）：", ""]
        for h in registry[-5:]:
            c = h["content"]
            brief = c.get("guess") or f"场景{c.get('scene')}动作{c.get('action')}成功率≈{c.get('predicted_success_rate')}"
            status_cn = {"pending": "待验证", "suspended": "证据不足暂停",
                         "verified": "已验证通过", "rejected": "已证伪丢弃"}.get(h["status"], h["status"])
            lines.append(f"  · [{status_cn}] {brief[:60]}")
            lines.append(f"    验证 {h['test_count']} 次（{h['success_count']}成/{h['fail_count']}败）"
                         f" 置信度 {h['confidence_raw']} → {h['final_confidence']}")
        lines.append("")
        lines.append("规则：验证次数≥2 且置信度≥0.6 才会写入长期记忆；≤0.3 直接丢弃；"
                     "热记忆只降权、永不删除。")
        return "\n".join(lines)


# ── 进程级单例：让工作记忆/假设注册表在多轮对话间存活（会话 = 进程生命周期） ──
# 说明：web 入口每条消息曾各自 new TanModel()，工作记忆会随请求销毁；
# 改用单例后，模块E/F 的会话内状态得以跨消息延续。开关关闭时单例与逐次实例化行为完全一致。
_TAN_MODEL_SINGLETON: Optional["TanModel"] = None


def get_tan_model() -> "TanModel":
    """获取进程级 TanModel 单例（模块E/F 会话状态的载体）。"""
    global _TAN_MODEL_SINGLETON
    if _TAN_MODEL_SINGLETON is None:
        _TAN_MODEL_SINGLETON = TanModel()
    return _TAN_MODEL_SINGLETON

ON: Optional["TanModel"] = None


def get_tan_model() -> "TanModel":
    """获取进程级 TanModel 单例（模块E/F 会话状态的载体）。"""
    global _TAN_MODEL_SINGLETON
    if _TAN_MODEL_SINGLETON is None:
        _TAN_MODEL_SINGLETON = TanModel()
    return _TAN_MODEL_SINGLETON

