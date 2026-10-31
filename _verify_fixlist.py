# -*- coding: utf-8 -*-
"""校验修复清单里的算术与内部一致性，不修改文件。"""
import re, json, io

P = r"D:\7tan\dsh-workspace\7tan.com-待修复清单.md"
t = io.open(P, encoding="utf-8").read()
lines = t.splitlines()
res = []
def chk(name, cond, detail=""):
    res.append(("PASS" if cond else "FAIL", name, detail))

# --- 1. sitemap 表算术 ---
TOTAL = 64405
rows = [(60488, "93.92"), (298, "0.46"), (120, "0.19"), (119, "0.18"),
        (116, "0.18"), (110, "0.17"), (3154, "4.90")]
s = sum(v for v, _ in rows)
chk("各行相加 == 64,405", s == TOTAL, "sum=%d" % s)
chk("剩余条数 3,154 与相减结果一致", TOTAL - (60488 + 298 + 120 + 119 + 116 + 110) == 3154, "")
pc = [round(v * 100.0 / TOTAL, 2) for v, _ in rows]
chk("各百分比与四舍五入一致", ["%.2f" % p for p in pc] == [x for _, x in rows], str(pc))
chk("百分比合计 100.00", abs(sum(pc) - 100.0) < 0.005, "sum=%.2f" % sum(pc))
chk("日期 6 + 45 = 51", 6 + 45 == 51, "")

# --- 2. 文件里写的数是否与上面一致 ---
for lit in ["60,488", "64,405", "298", "3,154", "93.92%", "0.46%", "4.90%", "51 个"]:
    chk("文中出现 %s" % lit, lit in t, "")

# --- 3. 总表条目数 == 正文章节条目数 ---
tbl = re.findall(r"^\|\s*(\d\.\d)\s*\|", t, re.M)
heads = re.findall(r"^###\s*(\d\.\d)\s", t, re.M)
p0 = sorted(set(x for x in tbl if x.startswith("1.")))
p1 = sorted(set(x for x in tbl if x.startswith("2.")))
p2 = sorted(set(x for x in tbl if x.startswith("3.")))
chk("总表 15 条", len(tbl) == 15, "tbl=%d" % len(tbl))
chk("章节 15 条且一一对应", sorted(set(tbl)) == sorted(heads), "heads=%d" % len(heads))
chk("P0=4 / P1=7 / P2=4", (len(p0), len(p1), len(p2)) == (4, 7, 4), str((len(p0), len(p1), len(p2))))

# --- 4. 断言表 False/True 数 ---
assert_rows = re.findall(r"^\|\s*([^|]+?)\s*\|\s*(?:\*\*)?(True|False)", t, re.M)
nf = sum(1 for _, v in assert_rows if v == "False")
nt = sum(1 for _, v in assert_rows if v == "True")
chk("断言表 14 行（12 False + 2 True）", (len(assert_rows), nf, nt) == (14, 12, 2),
    "rows=%d F=%d T=%d" % (len(assert_rows), nf, nt))

# --- 5. 与实测 JSON 对照（关键值） ---
src = json.load(io.open(r"D:\7tan\7tanAI\_fixcheck3_out.json", encoding="utf-8"))
chk("法务页三页均为 200", all(src["footer_pages"][k]["status"] == 200
    for k in ["/web/gywm.htm", "/web/lcwm.htm", "/web/bqsm.htm"]), "")
chk("about 392 / contact 289 / copyright 529",
    (src["footer_pages"]["/web/gywm.htm"]["plain_len"] == 392,
     src["footer_pages"]["/web/lcwm.htm"]["plain_len"] == 289,
     src["footer_pages"]["/web/bqsm.htm"]["plain_len"] == 529) == (True, True, True), "")

# --- 6. 排版检查 ---
bad = []
for i, ln in enumerate(lines):
    if ln.count("|") and not ln.startswith("|"):
        bad.append(i + 1)          # 表格外的竖线（代码块里允许）
chk("无 &amp; 实体残留", "&amp;" not in t, "")
chk("代码块数量为偶数", t.count("```") % 2 == 0, "count=%d" % t.count("```"))
chk("无 4 个以上连续空行", "\n\n\n\n" not in t, "")

print("行数 %d / 字符 %d" % (len(lines), len(t)))
for st, name, d in res:
    print("%-6s %-46s %s" % (st, name, d))
print("---- %d/%d PASS ----" % (sum(1 for r in res if r[0] == "PASS"), len(res)))
