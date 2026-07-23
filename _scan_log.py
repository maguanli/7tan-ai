import subprocess, os

# Use Python to search the log file directly
log_path = "logs/app_2026-07-24.log"
with open(log_path, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

keywords = ["stream_finished", "ChatPage", "TTS", "语音"]
for kw in keywords:
    count = content.count(kw)
    lines = [l for l in content.splitlines() if kw in l]
    print(f"\n=== '{kw}': {count} matches ===")
    for l in lines[-15:]:
        print(f"  {l[:250]}")
