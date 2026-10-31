# -*- coding: utf-8 -*-
"""1.0.23 发布清单更新：重命名 zip + version.json + index.html"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(r"D:\7tan\7tanAI")
REL = ROOT / "dist" / "release"
SRC_ZIP = REL / "7tan-editor-v1.0.23.zip"
DST_ZIP = REL / "7tan-editor-free-v1.0.23.zip"
WEB_ZIP = REL / "7tan-web-v1.0.23.zip"

VER = "1.0.23"
DATE = "2026-11-01"

NOTES = (
    "1.0.23 更新：上线全新 Agent 架构——AI 开始指挥 AI 干活。新增子 Agent 派工"
    "（spawn_worker / spawn_status）：主 Agent 拆解任务后派活给独立子 Agent，各自拥有独立会话"
    "与独立预算，跑完回传报告，主 Agent 核验结论；代码类任务自动分配独立 git worktree，"
    "多个 Worker 并行改代码不再互相踩踏。并发与安全：中止信号改为按作用域隔离（子任务超时不再"
    "误杀主 Agent 自己）、命令作用域围栏（无人值守时命令只能在指定目录内执行，越界直接拒绝）、"
    "命令全量审计（每条命令落盘，谁在何时执行了什么、结果如何都可事后追查）、资源租约"
    "（浏览器/桌面等独占资源排队，不再静默串窗）、每个 Worker 独立浏览器视图"
    "（浏览器不再是并发瓶颈，实测 3 个视图并行加载耗时 2.07 秒，串行需 6 秒以上）。"
    "发布质量：发帖后强制走独立断言闸门，闸门自身故障一律判失败（退出码 4），不再静默放行；"
    "验收结果增加幂等标记，避免重复全量验收；板块/用户/作者参数自动注入，不再吃默认值。"
    "安全加固：发布包脱敏范围扩展到发布凭据配置文件，服务器密码与 GitHub 令牌在构建时置空。"
    "修复：超长历史消息导致 AI 调用全部失败（400 maximum context length）、"
    "7723 平台游戏截图采集不到。"
)

fails = []


def md5_of(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------- 1. 重命名 zip ----------
if SRC_ZIP.exists():
    if DST_ZIP.exists():
        DST_ZIP.unlink()
    SRC_ZIP.rename(DST_ZIP)
    print(f"[1] 已重命名 -> {DST_ZIP.name}")
elif DST_ZIP.exists():
    print(f"[1] 目标名已存在，跳过重命名")
else:
    print("[1] [FAIL] 找不到构建产物 zip")
    sys.exit(1)

size = DST_ZIP.stat().st_size
md5 = md5_of(DST_ZIP)
print(f"    size={size}  md5={md5}")

# ---------- 2. version.json ----------
vj = ROOT / "website" / "updates" / "version.json"
data = json.loads(vj.read_text(encoding="utf-8"))
vers = data["versions"]

existing = [v for v in vers if v.get("version") == VER]
entry = {
    "version": VER,
    "channel": "stable",
    "platform": "windows",
    "url": f"https://www.7tan.com/updates/{DST_ZIP.name}",
    "md5": md5,
    "size": size,
    "notes": NOTES,
    "release_date": DATE,
}
if existing:
    vers.remove(existing[0])
    print("[2] version.json 已存在同版本，替换")
vers.insert(0, entry)
vj.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"[2] version.json 写入 {VER}，共 {len(vers)} 条")

# ---------- 3. index.html ----------
ix = ROOT / "website" / "updates" / "index.html"
html = ix.read_text(encoding="utf-8")
orig = html

# 3a. 旧最新标记去掉
html = html.replace('<td class="ver">v1.0.22（最新）</td>', '<td class="ver">v1.0.22</td>')

# 3b. 插入新行（若尚未插入）
if f'7tan-editor-free-v{VER}.zip' not in html.split("<tbody>", 1)[-1].split("</tbody>", 1)[0]:
    anchor = '<td class="ver">v1.0.22</td>'
    idx = html.find(anchor)
    if idx < 0:
        fails.append("index.html 找不到 v1.0.22 行锚点")
    else:
        tr_start = html.rindex("<tr>", 0, idx)
        line_start = html.rindex("\n", 0, tr_start) + 1
        indent = html[line_start:tr_start]
        row = (
            f'{indent}<tr>\n'
            f'{indent}  <td class="ver">v{VER}（最新）</td>\n'
            f'{indent}  <td class="date">{DATE}</td>\n'
            f'{indent}  <td>{size / 1024 / 1024:.1f} MB</td>\n'
            f'{indent}  <td><a class="btn" href="https://www.7tan.com/updates/{DST_ZIP.name}" download>⬇ 下载</a></td>\n'
            f'{indent}</tr>\n'
        )
        html = html[:line_start] + row + html[line_start:]
        print("[3] index.html 已插入下载行")

# 3c. 更新说明列表插入新条目
if f"<b>v{VER}</b>：" not in html:
    p_anchor = '<p class="note" style="color:#cbd5e1;">'
    pos = html.find(p_anchor)
    if pos < 0:
        fails.append("index.html 找不到更新说明容器")
    else:
        after = pos + len(p_anchor)
        nl = html.index("\n", after) + 1
        indent = re.match(r"[ \t]*", html[nl:]).group(0)
        html = html[:nl] + f"{indent}<b>v{VER}</b>：{NOTES}<br><br>\n" + html[nl:]
        print("[3] index.html 已插入更新说明")

if html != orig:
    ix.write_text(html, encoding="utf-8")

# ---------- 4. 自检 ----------
print("-" * 60)
checks = []
d2 = json.loads(vj.read_text(encoding="utf-8"))["versions"]
e = d2[0]
checks.append(("version.json 首条=1.0.23", e["version"] == VER))
checks.append(("md5 与文件一致", e["md5"] == md5))
checks.append(("size 与文件一致", e["size"] == size))
checks.append(("url 指向 -free- 名", e["url"].endswith(f"{DST_ZIP.name}")))
checks.append(("url 文件名真实存在", (REL / e["url"].rsplit("/", 1)[-1]).exists()))
h2 = ix.read_text(encoding="utf-8")
checks.append(("index.html 有新下载行", f'7tan-editor-free-v{VER}.zip' in h2))
checks.append(("index.html 最新标记唯一", h2.count("（最新）") == 1))
checks.append(("index.html 旧版本已去最新", '<td class="ver">v1.0.22（最新）</td>' not in h2))
checks.append(("index.html 有更新说明", f"<b>v{VER}</b>：" in h2))
checks.append(("HTML 标签配平 tbody", h2.count("<tbody>") == h2.count("</tbody>")))
checks.append(("HTML 标签配平 tr", h2.count("<tr>") == h2.count("</tr>")))

for name, ok in checks:
    print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    if not ok:
        fails.append(name)

print("-" * 60)
print(f"失败 {len(fails)} 项")
if fails:
    for f in fails:
        print("  -", f)
sys.exit(1 if fails else 0)
