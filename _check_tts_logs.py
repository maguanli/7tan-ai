import subprocess

# Search app log for TTS
r = subprocess.run(['findstr', '/i', 'TTS', 'logs\\app_2026-07-24.log'], 
                   capture_output=True, text=True)
print("=== app_2026-07-24.log TTS ===")
if r.stdout:
    lines = r.stdout.strip().splitlines()
    for l in lines[-20:]:
        print(l)
else:
    print("NO TTS MESSAGES FOUND")

# Also check error log
r2 = subprocess.run(['findstr', '/i', 'TTS', 'logs\\error_2026-07-24.log'],
                    capture_output=True, text=True)
print("\n=== error_2026-07-24.log TTS ===")
if r2.stdout:
    print(r2.stdout.strip())
else:
    print("NO TTS MESSAGES")

# Also check yesterday
r3 = subprocess.run(['findstr', '/i', 'TTS', 'logs\\app_2026-07-23.log'],
                    capture_output=True, text=True)
print("\n=== app_2026-07-23.log TTS ===")
if r3.stdout:
    lines = r3.stdout.strip().splitlines()
    for l in lines[-10:]:
        print(l)
else:
    print("NO TTS MESSAGES")
