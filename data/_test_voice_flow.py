"""完整模拟语音持久化流程，找出断点"""
import json, os, sys

# 1. 模拟 _voice_settings_path()
from pathlib import Path
cwd = Path(os.getcwd())
print(f"[TEST] cwd = {cwd}")

voice_path = None
for p in [cwd] + list(cwd.parents):
    if (p / "config" / "config.yaml").exists():
        voice_path = str(p / "data" / "voice_settings.json")
        print(f"[TEST] 找到 config.yaml at: {p}")
        break

if not voice_path:
    voice_path = str(Path("src/ui/chat_page.py").parent.parent.parent / "data" / "voice_settings.json")
    print(f"[TEST] 回退路径: {voice_path}")

print(f"[TEST] voice_settings.json 路径: {voice_path}")
print(f"[TEST] 文件是否存在: {os.path.exists(voice_path)}")

# 2. 读当前值
if os.path.exists(voice_path):
    with open(voice_path, "r", encoding="utf-8") as f:
        current = json.load(f)
    print(f"[TEST] 当前内容: {current}")
else:
    current = {"voice_gender": "female", "voice_mode": False}
    print(f"[TEST] 文件不存在，默认: {current}")

# 3. 模拟切换为 male
current["voice_gender"] = "male"
current["voice_mode"] = False

# 4. 写入
os.makedirs(os.path.dirname(voice_path), exist_ok=True)
with open(voice_path, "w", encoding="utf-8") as f:
    json.dump(current, f, indent=2)
print(f"[TEST] 已写入: {current}")

# 5. 读回验证
with open(voice_path, "r", encoding="utf-8") as f:
    verify = json.load(f)
print(f"[TEST] 读回验证: {verify}")
print(f"[TEST] 结果: {'PASS' if verify.get('voice_gender') == 'male' else 'FAIL'}")
