# -*- coding: utf-8 -*-
"""发布后全链路验收"""
import os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests

MIRROR = r'D:\7tan\repo-filtered.git'
BRANCH = 'backup/20261011-local'

print('=' * 60)
print('1. GitHub 分支')
print('=' * 60)
p = subprocess.run(['git', 'ls-remote', '--heads', 'origin', BRANCH], cwd=MIRROR,
                   capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
print('  ' + (p.stdout.strip() or '(不存在)'))
p2 = subprocess.run(['git', 'rev-parse', BRANCH], cwd=MIRROR, capture_output=True,
                    text=True, encoding='utf-8', errors='replace')
local = p2.stdout.strip()
print('  本地 HEAD:', local)
remote = p.stdout.split()[0] if p.stdout.strip() else ''
print('  一致:', 'YES' if remote == local else 'NO')

print('\n' + '=' * 60)
print('2. 下载站文件（HTTP 实测）')
print('=' * 60)
for path, expect in (
    ('/updates/7tan-editor-free-v1.0.23.zip', 419870967),
    ('/updates/7tan-editor-free-v1.0.23.zip.sig', 346),
    ('/updates/7tan-web-v1.0.23.zip', 60760680),
    ('/updates/7tan-web-v1.0.23.zip.sig', 346),
    ('/updates/version.json', None),
    ('/updates/index.html', None),
):
    url = 'https://www.7tan.com' + path
    try:
        r = requests.head(url, timeout=25, allow_redirects=True)
        cl = r.headers.get('Content-Length', '?')
        ok = (r.status_code == 200)
        if expect and cl.isdigit():
            ok = ok and int(cl) == expect
        print('  [%s] %-45s %d  %s B' % ('OK  ' if ok else 'FAIL', path, r.status_code, cl))
    except Exception as e:
        print('  [FAIL] %-45s %s' % (path, type(e).__name__))

print('\n' + '=' * 60)
print('3. 995 页面')
print('=' * 60)
r = requests.get('https://www.7tan.com/game/995/', timeout=30,
                 headers={'User-Agent': 'Mozilla/5.0'})
html = r.text
checks = {
    '标题含 v1.0.23': 'v1.0.23' in html,
    '不含 v1.0.22': 'v1.0.22' not in html,
    '下载链接指向新包': '7tan-editor-free-v1.0.23.zip' in html,
    '不含旧包链接': '7tan-editor-free-v1.0.22.zip' not in html,
    '含 419,870,967': '419,870,967' in html or '419870967' in html,
}
for k, v in checks.items():
    print('  [%s] %s' % ('OK  ' if v else 'FAIL', k))

print('\n' + '=' * 60)
print('4. ai-tool 下载页')
print('=' * 60)
r = requests.get('https://www.7tan.com/ai-tool/', timeout=30,
                 headers={'User-Agent': 'Mozilla/5.0'})
h = r.text
for k, v in {
    '显示 v1.0.23': 'v1.0.23' in h,
    '下载按钮指向新包': '7tan-editor-free-v1.0.23.zip' in h,
    'JSON-LD 版本 1.0.23': '"softwareVersion":"1.0.23"' in h.replace(' ', ''),
}.items():
    print('  [%s] %s' % ('OK  ' if v else 'FAIL', k))
