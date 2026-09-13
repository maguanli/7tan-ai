# -*- coding: utf-8 -*-
"""路径A：问句语义解析器回归测试（纯规则，无第三方模型）。

覆盖：
  1. 疑问类型识别 + 主体提取（数量/定义/身份/位置/时间/原因/怎么做）
  2. 检索改写（「太阳系有多少颗行星」→「太阳系 有几颗 行星」）
  3. 答案抽取优先级（阿拉伯数字 > 中文数字，避免「九大行星」这类传统说法）

运行：python tests/test_question_parser.py
"""
import sys
import io
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

WM = ROOT / "src" / "agent" / "world_model.py"
py_compile.compile(str(WM), doraise=True)

from src.agent.world_model import parse_question, extract_quantity_answer

CASES = [
    ("太阳系有多少颗行星？", "quantity", "太阳系 有几颗 行星"),
    ("太阳系有几颗行星", "quantity", "太阳系 有几颗 行星"),
    ("中国有多少个省份", "quantity", "中国 有几个 省份"),
    ("地球有多少人口", "quantity", "地球 人口 数量"),
    ("人工智能是什么", "definition", "人工智能 是什么"),
    ("什么是人工智能", "definition", "人工智能 是什么"),
    ("老马是谁", "identity", "老马"),
    ("长城在哪里", "location", "长城 在哪里"),
    ("为什么天空是蓝色的", "reason", "为什么 天空是蓝色的"),
    ("怎么做红烧肉", "how_to", "如何 红烧肉"),
    ("你会写脚本吗", None, None),
]

failed = 0
for text, exp_type, exp_query in CASES:
    p = parse_question(text)
    if exp_type is None:
        ok = p is None
    else:
        ok = p is not None and p.qtype == exp_type and p.build_search_query() == exp_query
    if not ok:
        failed += 1
        print(f"FAIL [{text}] -> {p.qtype if p else None} / {p.build_search_query() if p else None}")

# 答案抽取优先级：阿拉伯数字优先（「8颗行星」优先于「九大行星」）
qp = parse_question("太阳系有多少颗行星")
res = "1. **九大行星_百度百科** 九大行星是指八大行星与冥王星。\n2. **8颗行星_百度百科** 八大行星（8 Planets）。"
a = extract_quantity_answer(qp, res)
if a != "8颗行星":
    failed += 1
    print(f"FAIL 抽取答案: {a!r}（期望 '8颗行星'）")

if failed == 0:
    print("ALL_PASS")
else:
    print(f"SOME_FAIL ({failed})")
    sys.exit(1)
