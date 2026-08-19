import os

user = os.environ.get('USERNAME', 'Administrator')
prefs_src = f'C:\\Users\\{user}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Preferences'
secure_src = f'C:\\Users\\user}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Secure Preferences'
chrome_dir = f'C:\\Users\\{user}\\AppData\\Local\\Google\\Chrome\\User Data\\Default'

# Create a comprehensive Python fix script
py_content = f'''import os, json, subprocess, time

src = r'{prefs_src}'
src_sec = r'{os.path.join(chrome_dir, "Secure Preferences")}'

# Kill Chrome
subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True)
time.sleep(2)

for path in [src, src_sec]:
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        data.setdefault('session', {{}})
        data['session']['restore_on_startup'] = 4
        data['session']['startup_urls'] = []
        # Write to temp then replace
        tmp = path + '.fixed'
        with open(tmp, 'w', encoding='utf-8-sig') as f:
            json.dump(data, f, ensure_ascii=False)
        os.remove(path)
        os.rename(tmp, path)
        print(f"Fixed: {{path}}")
    except Exception as e:
        print(f"Error {{path}}: {{e}}")

# Delete journals
for jf in ['Preferences-journal', 'Secure Preferences-journal']:
    jp = os.path.join(r'{chrome_dir}', jf)
    if os.path.exists(jp):
        try: os.remove(jp)
        except: pass

# Launch Chrome
time.sleep(1)
os.startfile(r'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')
print("Chrome launched!")
'''

py_path = os.path.join(os.path.dirname(prefs_src), '..', '..', '..', '..', 'fix_chrome_prefs.py')
# Actually put it somewhere accessible
py_path = r'D:\\fix_chrome_prefs.py'
# Hmm the D: drive also can't be written... Let me use the data dir
py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fix_chrome_prefs.py')

print(f"Python script: {py_path}")
print(f"Prefs path: {prefs_src}")
print(f"Chrome dir: {chrome_dir}")
