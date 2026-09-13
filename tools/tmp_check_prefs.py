# -*- coding: utf-8 -*-
"""检查打包版运行后的用户偏好文件与全局配置"""
import sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

base = Path(r"C:\7tan-test\7tan-editor")

print("===== data/users/ =====")
ud = base / "data" / "users"
if ud.exists():
    for f in ud.glob("*.json"):
        print(f"\n--- {f.name} ---")
        try:
            print(json.dumps(json.loads(f.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
        except Exception as e:
            print("读取失败:", e)
else:
    print("(不存在)")

print("\n===== config/config.yaml 的 app 段 =====")
cfg = base / "config" / "config.yaml"
if cfg.exists():
    import yaml
    d = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    print("app =", d.get("app"))
    print("ai.active =", (d.get("ai") or {}).get("active"))
    print("顶层键:", sorted(d.keys()))
else:
    print("(不存在)")
