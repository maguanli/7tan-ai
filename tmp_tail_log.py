import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
lines = open('build_full_log.txt', 'r', encoding='utf-8', errors='replace').readlines()
print(''.join(lines[:35]))
print('====== MID ======')
print(''.join(lines[200:248]))
