import os, json, shutil, subprocess

src = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default\Preferences'
src_sec = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default\Secure Preferences'
tmp = r'D:\temp_chrome_prefs.json'
tmp_sec = r'D:\temp_chrome_sec.json'

# Copy files
shutil.copy2(src, tmp)
shutil.copy2(src_sec, tmp_sec)
print("Files copied")

# Modify
with open(tmp, 'r', encoding='utf-8-sig') as f:
    prefs = json.load(f)
print(f"Before: {prefs.get('session', {})}")
prefs.setdefault('session', {})
prefs['session']['restore_on_startup'] = 4
prefs['session']['startup_urls'] = []
with open(tmp, 'w', encoding='utf-8-sig') as f:
    json.dump(prefs, f, ensure_ascii=False)

with open(tmp_sec, 'r', encoding='utf-8-sig') as f:
    sec = json.load(f)
sec.setdefault('session', {})
sec['session']['restore_on_startup'] = 4
with open(tmp_sec, 'w', encoding='utf-8-sig') as f:
    json.dump(sec, f, ensure_ascii=False)
print("Files modified")

# Create bat
bat = r'D:\fix_chrome_prefs.bat'
journal1 = os.path.join(os.path.dirname(src), 'Preferences-journal')
journal2 = os.path.join(os.path.dirname(src), 'Secure Preferences-journal')
content = f'''@echo off
copy /Y "D:\\temp_chrome_prefs.json" "{src}" >nul
copy /Y "D:\\temp_chrome_sec.json" "{src_sec}" >nul
del "{journal1}" >nul 2>&1
del "{journal2}" >nul 2>&1
echo Chrome preferences fixed! restore_on_startup = 4
'''
with open(bat, 'w', encoding='gbk') as f:
    f.write(content)
print(f"Batch created: {bat}")

# Try to run as admin
print("\nTrying to run batch as admin...")
try:
    r = subprocess.run(
        ['powershell', '-Command', 
         f'Start-Process cmd -ArgumentList \'/c {bat}\' -Verb RunAs -Wait -PassThru'],
        capture_output=True, text=True, timeout=30
    )
    print(f"Result: returncode={r.returncode}")
    if r.stdout.strip(): print(f"stdout: {r.stdout.strip()}")
    if r.stderr.strip(): print(f"stderr: {r.stderr.strip()}")
except Exception as e:
    print(f"Error: {e}")

# Verify
try:
    with open(src, 'r', encoding='utf-8-sig') as f:
        v = json.load(f)
    val = v.get('session', {}).get('restore_on_startup', 'NOT SET')
    print(f"\nVerified: restore_on_startup = {val}")
    if val == 4:
        print("SUCCESS!")
    else:
        print("FAILED - file was not updated (Chrome may have it locked)")
except Exception as e:
    print(f"Verify error: {e}")
