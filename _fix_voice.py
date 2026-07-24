import re

path = r'src\ui\chat_page.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '        print(f"[Voice] 切换为: {self._voice_gender}")\n\n        # 持久化保存\n        self._save_voice_gender()\n\n        try:\n            from data.plugins.tts_piper.tools import tts_set_gender\n            result = tts_set_gender(self._voice_gender)\n            print(f"[Voice] TTS 引擎切换结果: {result}")\n        except Exception as e:\n            print(f"[Voice] TTS 引擎切换失败: {e}")'

if old in content:
    print('找到旧代码')
    new = """        import sys
        sys.stderr.write(f"[Voice] 切换为: {self._voice_gender}\\n")
        sys.stderr.flush()

        # 直接写入数据库
        try:
            import sqlite3
            from pathlib import Path
            db_path = str(Path(__file__).resolve().parent.parent.parent / "data" / "games.db")
            sys.stderr.write(f"[Voice] 写入DB: {db_path}\\n")
            con = sqlite3.connect(db_path)
            cur = con.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute("INSERT INTO app_settings (key, value) VALUES ('voice_gender', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (self._voice_gender,))
            cur.execute("INSERT INTO app_settings (key, value) VALUES ('voice_mode', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("true" if self._voice_mode else "false",))
            con.commit()
            con.close()
            sys.stderr.write(f"[Voice] DB写入成功: gender={self._voice_gender}, mode={self._voice_mode}\\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"[Voice] DB写入失败: {e}\\n")
            sys.stderr.flush()

        try:
            from data.plugins.tts_piper.tools import tts_set_gender
            result = tts_set_gender(self._voice_gender)
            sys.stderr.write(f"[Voice] TTS 引擎切换结果: {result}\\n")
        except Exception as e:
            sys.stderr.write(f"[Voice] TTS 引擎切换失败: {e}\\n")"""
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('替换成功')
else:
    print('未找到旧代码')
    idx = content.find('[Voice] 切换为:')
    if idx >= 0:
        print('找到位置:', idx)
        print(repr(content[idx:idx+500]))
