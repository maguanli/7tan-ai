import os, json, shutil, time, subprocess

src = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default\Preferences'
src_sec = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default\Secure Preferences'
tmp = r'C:\temp_chrome_prefs.json'
tmp_sec = r'C:\temp_chrome_sec.json'

# Copy files out
shutil.copy2(src, tmp)
shutil.copy2(src_sec, tmp_sec)
print("Copied files out")

# Modify copies
with open(tmp, 'r', encoding='utf-8-sig') as f:
    prefs = json.load(f)
print(f"Before: {prefs.get('session', {})}")
prefs.setdefault('session', {})
prefs['session']['restore_on_startup'] = 4
prefs['session']['startup_urls'] = []
with open(tmp, 'w', encoding='utf-8-sig') as f:
    json.dump(prefs, f, ensure_ascii=False)
print(f"After: restore_on_startup = {prefs['session']['restore_on_startup']}")

with open(tmp_sec, 'r', encoding='utf-8-sig') as f:
    sec = json.load(f)
sec.setdefault('session', {})
sec['session']['restore_on_startup'] = 4
with open(tmp_sec, 'w', encoding='utf-8-sig') as f:
    json.dump(sec, f, ensure_ascii=False)
print("Secure prefs modified")

# Create a batch file that will replace the originals with admin
bat_content = f'''@echo off
echo Replacing Chrome prefs...
copy /Y "{tmp}" "{src}" >nul
copy /Y "{tmp_sec}" "{src_sec}" >nul
del "{os.path.join(os.path.dirname(src), 'Preferences-journal')}" >nul 2>&1
echo Done! restore_on_startup set to 4 (restore last session)
'''
bat_path = r'C:\fix_chrome_prefs.bat'
with open(bat_path, 'w', encoding='gbk') as f:
    f.write(bat_content)
print(f"Created batch: {bat_path}")

# Try to run the batch with admin privileges
try:
    r = subprocess.run(['powershell', '-Command', f'Start-Process cmd -ArgumentList \'/c {bat_path}\' -Verb RunAs -Wait'], 
                       capture_output=True, text=True, timeout=30)
    print(f"Admin batch result: {r.returncode}")
    print(r.stdout)
    if r.stderr:
        print(f"stderr: {r.stderr}")
except Exception as e:
    print(f"Admin batch error: {e}")

# Verify
try:
    with open(src, 'r', encoding='utf-8-sig') as f:
        v = json.load(f)
    print(f"Verified: restore_on_startup = {v['session'].get('restore_on_startup', 'NOT SET')}")
except:
    print("Could not verify (file may still be locked)")
    print("Please run the batch file manually: right-click C:\fix_chrome_prefs.bat -> Run as administrator")
