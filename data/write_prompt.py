import sqlite3
from pathlib import Path

# 1. Read optimized prompt
prompt_path = Path(r"D:\7tan\7tanAI\dist\7tan-editor\_internal\data\prompts\system.txt")
new_content = prompt_path.read_text(encoding='utf-8')
print(f"[1] File read: {len(new_content)} chars")

# 2. Write to database
db_path = Path(r"D:\7tan\7tanAI\data\games.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check old version
cursor.execute("SELECT prompt_type, char_count, updated_at FROM prompts WHERE prompt_type='system'")
old = cursor.fetchone()
if old:
    print(f"[2] DB old version: {old[1]} chars, updated {old[2]}")
else:
    print(f"[2] DB old version: NOT FOUND")

# Write new version
cursor.execute("""
    INSERT INTO prompts (prompt_type, content, char_count, updated_at)
    VALUES ('system', ?, ?, datetime('now', 'localtime'))
    ON CONFLICT(prompt_type) DO UPDATE SET
        content = excluded.content,
        char_count = excluded.char_count,
        updated_at = excluded.updated_at
""", (new_content, len(new_content)))
conn.commit()

# Verify
cursor.execute("SELECT prompt_type, char_count, updated_at FROM prompts WHERE prompt_type='system'")
new = cursor.fetchone()
print(f"[3] DB new version: {new[1]} chars, updated {new[2]}")
print(f"    Verify: {'OK' if new[1] == len(new_content) else 'FAIL'}")

conn.close()

# 3. Delete empty shell database
empty_db = Path(r"D:\7tan\7tanAI\data\7tan.db")
if empty_db.exists():
    size = empty_db.stat().st_size
    if size == 0:
        empty_db.unlink()
        print(f"[4] Deleted empty: 7tan.db ({size} bytes)")
    else:
        print(f"[4] Skipped: 7tan.db not empty ({size} bytes)")
else:
    print(f"[4] 7tan.db does not exist")

# 4. Check sandbox residual
sandbox_db = Path(r"D:\7tan\7tanAI\data\sandbox\data\games.db")
if sandbox_db.exists() and sandbox_db.stat().st_size == 0:
    sandbox_db.unlink()
    print(f"[5] Deleted sandbox residual: games.db")

print("\nAll done!")