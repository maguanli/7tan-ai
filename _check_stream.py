import subprocess

# Search for stream_finished and _on_response in today's log
for pattern in ["stream_finished", "ChatPage", "_on_response", "_speak_response"]:
    r = subprocess.run(['findstr', '/i', pattern, 'logs\\app_2026-07-24.log'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace')
    lines = r.stdout.strip().splitlines() if r.stdout else []
    print(f"\n=== {pattern} ({len(lines)} matches) ===")
    for l in lines[-10:]:
        print(l[:200])
