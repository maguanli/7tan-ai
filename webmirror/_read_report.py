import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb\_mirror_report.txt'
t = open(p, encoding='utf-8', errors='replace').read()
print(t[:2500])
print('...')
print('LEN', len(t))
