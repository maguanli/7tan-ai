import os, json, shutil

# Use user temp dir
user_temp = os.environ.get('TEMP', os.environ.get('TMP', r'C:\Users\Administrator\AppData\Local\Temp'))
src = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default\Preferences'
src_sec = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default\Secure Preferences'
tmp = os.path.join(user_temp, 'chrome_prefs_fixed.json')
tmp_sec = os.path.join(user_temp, 'chrome_sec_fixed.json')

print(f"Temp dir: {user_temp}")

# Copy
shutil.copy2(src, tmp)
shutil.copy2(src_sec, tmp_sec)
print("Copied")

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
print("Modified")

# Create bat
bat = os.path.join(user_temp, 'fix_chrome.bat')
chrome_dir = os.path.dirname(src)
journal1 = os.path.join(chrome_dir, 'Preferences-journal')
journal2 = os.path.join(chrome_dir, 'Secure Preferences-journal')

content = f'''@echo off
echo Stopping Chrome...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo Copying fixed preferences...
copy /Y "{tmp}" "{src}" >nul
copy /Y "{tmp_sec}" "{src_sec}" >nul
del "{journal1}" >nul 2>&1
del "{journal2}" >nul 2>&1
echo Launching Chrome...
start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
echo Done!
'''
with open(bat, 'w', encoding='gbk') as f:
    f.write(content)
print(f"Batch: {bat}")
print("DONE - run the batch file")
