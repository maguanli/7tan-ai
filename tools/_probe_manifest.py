import json, sys
d = json.load(open(r"D:\7tan\7tanAI\integrity.json", encoding="utf-8"))
key = "files"
raw = d.get(key)
if isinstance(raw, dict):
    fs = list(raw.keys())
else:
    fs = [f.get("path") if isinstance(f, dict) else f for f in raw]
print("清单条目数:", len(fs))
want = ("optimizer", "tool_executor", "abort_signal", "cmd_scope", "browser", "desktop", "agent_loop", "registry")
for w in want:
    hit = [p for p in fs if w in str(p)]
    print(f"  {w:16s} -> {hit if hit else '不在清单（可自由改）'}")
print("\n完整清单:")
for p in sorted(fs):
    print("   ", p)
