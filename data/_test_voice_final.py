"""端到端模拟：模拟 chat_page._voice_settings_path 的行为"""
import json, os, sys
from pathlib import Path

# 模拟 _voice_settings_path 的新实现
def voice_settings_path():
    return str(Path(__file__).resolve().parent.parent.parent / "data" / "voice_settings.json")

path = voice_settings_path()
print(f"1. 路径: {path}")
print(f"2. 文件存在: {os.path.exists(path)}")

# 模拟加载
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"3. 当前内容: {data}")

# 模拟切换为 male
data["voice_gender"] = "male"
data["voice_mode"] = False

# 模拟保存
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print(f"4. 已写入: {data}")

# 读回验证
with open(path, "r", encoding="utf-8") as f:
    verify = json.load(f)
print(f"5. 读回: {verify}")
print(f"6. 结果: {'✅ PASS' if verify.get('voice_gender') == 'male' else '❌ FAIL'}")
