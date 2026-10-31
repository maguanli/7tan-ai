# -*- coding: utf-8 -*-
"""说明书两副本一致性 + HTML 结构完整性检查

说明书有两份副本，内容必须完全一致：
  ① templates/7Tan使用说明书.html  —— 打进发布包
  ② website/manual.html            —— 线上官网
历史上出现过只改一份导致线上与包内版本不一致的问题，故独立成检查。

用法: python tools/manual_sync_check.py
退出码: 0 全通过 / 1 有失败
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "templates", "7Tan使用说明书.html")
B = os.path.join(ROOT, "website", "manual.html")

a = io.open(A, encoding="utf-8").read()
b = io.open(B, encoding="utf-8").read()

ok, bad = [], []


def chk(name, cond, detail=""):
    (ok if cond else bad).append(
        ("[PASS] " if cond else "[FAIL] ") + name + (" " + detail if detail else ""))


chk("两副本内容完全一致", a == b,
    "" if a == b else "长度 %d vs %d" % (len(a), len(b)))

for label, s in (("templates", a), ("website", b)):
    chk(label + " <tr> 与 </tr> 配对", s.count("<tr>") == s.count("</tr>"),
        "%d / %d" % (s.count("<tr>"), s.count("</tr>")))
    chk(label + " <td> 与 </td> 配对", s.count("<td>") == s.count("</td>"),
        "%d / %d" % (s.count("<td>"), s.count("</td>")))
    # 版本号应出现在 5 处：标题、正文版本、压缩包名、更新记录首行、页脚
    chk(label + " 当前版本号共 5 处", s.count("v1.0.23") == 5,
        "出现 %d 次" % s.count("v1.0.23"))
    chk(label + " v1.0.22 更新记录仍在（历史保留）", "v1.0.22" in s)
    chk(label + " 无残留旧版本声明", "版本 v1.0.22" not in s and "说明书 v1.0.22" not in s)

print("\n".join(ok))
if bad:
    print("\n".join(bad))
print("\n结果: %s (%d 通过 / %d 失败)" % (
    "全部通过" if not bad else "有失败", len(ok), len(bad)))
