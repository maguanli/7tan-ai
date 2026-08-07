import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
data = open(r'D:\7tan\7tanAI\build.spec', 'r', encoding='utf-8', errors='replace').read()
for line in data.splitlines():
    if 'noarchive' in line or 'version=' in line:
        print(line)
