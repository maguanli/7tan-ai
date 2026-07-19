import re

app_path = r"D:\7tan\7tanAI\src\ui\app.py"
with open(app_path, "r", encoding="utf-8") as f:
    app_lines = f.readlines()

has_video_import = any("VideoEditorPage" in l for l in app_lines)
print(f"[app.py] VideoEditorPage import: {'OK' if has_video_import else 'MISSING'}")

for i, l in enumerate(app_lines):
    if "VideoEditorPage" in l:
        print(f"  line {i+1}: {l.strip()}")

chat_path = r"D:\7tan\7tanAI\src\ui\chat_page.py"
with open(chat_path, "r", encoding="utf-8") as f:
    chat_lines = f.readlines()

sidebar_ref_lines = [i for i, l in enumerate(chat_lines) if "_sidebar_ref" in l]
print(f"\n[chat_page.py] _sidebar_ref references: {len(sidebar_ref_lines)}")
for i in sidebar_ref_lines[:15]:
    print(f"  line {i+1}: {chat_lines[i].strip()}")

for i, l in enumerate(chat_lines):
    if "def _refresh_sessions" in l:
        print(f"\n[chat_page.py] _refresh_sessions at line {i+1}:")
        for j in range(i, min(i+25, len(chat_lines))):
            print(f"  {j+1}: {chat_lines[j].rstrip()}")
        break

for i, l in enumerate(chat_lines):
    if "def attach_external_sidebar" in l:
        print(f"\n[chat_page.py] attach_external_sidebar at line {i+1}:")
        for j in range(i, min(i+35, len(chat_lines))):
            print(f"  {j+1}: {chat_lines[j].rstrip()}")
        break

print("\n--- QTimer + auto_load ---")
for i, l in enumerate(chat_lines):
    if "QTimer" in l and ("auto_load" in l or "load_sessions" in l):
        print(f"  line {i+1}: {l.strip()}")
