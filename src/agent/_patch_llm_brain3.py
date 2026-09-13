# -*- coding: utf-8 -*-
"""临时补丁3：言语层误拦时间问题（用后即删）"""
import io
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

p = "world_model.py"
s = io.open(p, encoding="utf-8").read()

pairs = [
    # 在 speech 言语层前插入：外部时间/日期快速通道（避免「现在几点了」被误分类为感知自述）
    (
"""        # 2) 言语层（自述类问题）
        speech = self.speech.respond(text)
        if speech is not None:
            logger.info(f"🌍 7Tan模型 → 言语自述（意图={self.speech._last_intent}）")
            return speech""",
"""        # 1.9) 外部时间/日期快速通道（零成本、本机时间；避免「现在几点了」被言语层
        #      误分类为「感知自述」而答非所问）
        if re.search(r"(现在几|几点|星期几|几号|今天.*(时间|日期)|现在.*(时间|几点))", text):
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            wd = {"Mon": "一", "Tue": "二", "Wed": "三", "Thu": "四",
                  "Fri": "五", "Sat": "六", "Sun": "日"}.get(time.strftime("%a"), "?")
            return f"🕐 现在是 {now}，星期{wd}（本机系统时间，真实可靠）。"
        # 2) 言语层（自述类问题）
        speech = self.speech.respond(text)
        if speech is not None:
            logger.info(f"🌍 7Tan模型 → 言语自述（意图={self.speech._last_intent}）")
            return speech""",
    ),
]

for i, (old, new) in enumerate(pairs, 1):
    n = s.count(old)
    print(f"[{i}] match={n} | {old.splitlines()[0][:70]}")
    if n == 1:
        s = s.replace(old, new)
        print("    [OK] replaced")
    elif n == 0:
        print("    [SKIP] not found (maybe already patched)")
    else:
        print(f"    [WARN] multiple={n}, skipped (need manual)")

io.open(p, "w", encoding="utf-8").write(s)
print("write done")
