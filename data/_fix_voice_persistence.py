"""一次性脚本：替换 chat_page.py 中的语音持久化方法"""
import re

with open('src/ui/chat_page.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_start = '# ---- 语音性别持久化（JSON 文件 + QSettings 双写）----'
old_end = '    def _toggle_voice_mode(self):'

idx_start = content.find(old_start)
idx_end = content.find(old_end, idx_start)

if idx_start == -1:
    print("ERROR: start marker not found")
elif idx_end == -1:
    print("ERROR: end marker not found")
else:
    new_code = '''# ---- 语音性别持久化（JSON 文件，写入后立即验证）----

    @staticmethod
    def _voice_settings_path():
        """获取 voice_settings.json 路径"""
        from pathlib import Path
        import os
        cwd = Path(os.getcwd())
        for p in [cwd] + list(cwd.parents):
            if (p / "config" / "config.yaml").exists():
                return str(p / "data" / "voice_settings.json")
        return str(Path(__file__).parent.parent.parent / "data" / "voice_settings.json")

    def _load_voice_gender(self):
        """从 JSON 文件恢复语音设置"""
        import json, os
        path = self._voice_settings_path()
        print(f"[Voice] 加载路径: {path}")
        print(f"[Voice] 文件存在: {os.path.exists(path)}")

        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                gender = data.get("voice_gender", "female")
                mode = data.get("voice_mode", False)
                print(f"[Voice] JSON读取成功: gender={gender}, mode={mode}")
                if gender in ("female", "male"):
                    self._voice_gender = gender
                self._voice_mode = bool(mode)
                print(f"[Voice] 已恢复: gender={self._voice_gender}, mode={self._voice_mode}")
            except Exception as e:
                print(f"[Voice] JSON读取异常: {e}")
                self._voice_gender = "female"
                self._voice_mode = False
        else:
            print("[Voice] 首次使用，创建默认设置: female")
            self._voice_gender = "female"
            self._voice_mode = False
            self._save_voice_gender()

        try:
            from data.plugins.tts_piper.tools import tts_set_gender
            tts_set_gender(self._voice_gender)
        except Exception as e:
            print(f"[Voice] TTS引擎设置失败: {e}")

    def _save_voice_gender(self):
        """持久化语音设置到 JSON 文件（写入后立即读回验证）"""
        import json, os
        path = self._voice_settings_path()
        data = {
            "voice_gender": self._voice_gender,
            "voice_mode": self._voice_mode,
        }
        print(f"[Voice] 准备写入: {data}")
        print(f"[Voice] 写入路径: {path}")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[Voice] JSON写入完成")
            # 立即读回验证
            with open(path, "r", encoding="utf-8") as f:
                verify = json.load(f)
            if verify.get("voice_gender") == self._voice_gender:
                print(f"[Voice] 验证通过: {verify}")
            else:
                print(f"[Voice] 验证失败! 写入={data}, 读回={verify}")
        except Exception as e:
            print(f"[Voice] 写入异常: {type(e).__name__}: {e}")

'''

    content = content[:idx_start] + new_code + content[idx_end:]
    
    with open('src/ui/chat_page.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("SUCCESS: voice persistence code replaced")

    # Verify
    with open('src/ui/chat_page.py', 'r', encoding='utf-8') as f:
        new_content = f.read()
    if '_voice_settings_path' in new_content:
        print("VERIFY: new methods present in file")
    if '_db_get_setting' in new_content:
        print("WARNING: old _db_get_setting still present!")
    else:
        print("VERIFY: old _db_get_setting removed")
    if '_QSET' in new_content:
        print("WARNING: old _QSET still present!")
    else:
        print("VERIFY: old _QSET removed")
