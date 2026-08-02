# -*- coding: utf-8 -*-
"""审计第 3 部分：补充验证"""
import os, re, zipfile

log = lambda *a: print(*a)

# ========== 1. exe 中 api_key/secret/token 上下文 ==========
log('=' * 60)
log('[16] exe 字符串上下文（区分变量名/真实密钥）')
log('=' * 60)
exe = r'D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe'
data = open(exe, 'rb').read()
# 找 sk- 开头 30+ 字符的疑似真实 key
sk = re.findall(rb'sk-[A-Za-z0-9]{20,}', data)
log(f'  疑似真实 API key (sk-xxx): {len(sk)} 个')
for s in sk[:5]:
    log(f'    ⚠️  {s.decode(errors="ignore")[:40]}')
# AKID / LTAI (阿里云)
ak = re.findall(rb'(?:AKID|LTAI)[A-Za-z0-9]{15,}', data)
log(f'  疑似云厂商 AccessKey: {len(ak)} 个')
for a in ak[:5]:
    log(f'    ⚠️  {a.decode(errors="ignore")[:40]}')
# 找 'api_key' 上下文
idx = 0
cnt = 0
for m in re.finditer(rb'.{30}api_key.{30}', data):
    log(f'  ctx: ...{m.group().decode(errors="ignore")}...')
    cnt += 1
    if cnt >= 8:
        break
log(f'  api_key 上下文共展示 {cnt} 处')

# ========== 2. _build 里 auth_client_broken.pyd 及更新清单 ==========
log('')
log('=' * 60)
log('[17] _build 中的 broken pyd 与更新机制文件')
log('=' * 60)
build = r'D:\7tan\7tanAI\dist\_build'
if os.path.exists(build):
    for dp, dn, fn in os.walk(build):
        for f in fn:
            if 'broken' in f.lower() or 'manifest' in f.lower() or 'update' in f.lower() or f.endswith('.sig'):
                fp = os.path.join(dp, f)
                log(f'  {os.path.relpath(fp, build)} ({os.path.getsize(fp):,} B)')
# 检查 build.spec 中 broken 引用
spec = os.path.join(build, 'build.spec')
if os.path.exists(spec):
    content = open(spec, encoding='utf-8').read()
    log(f'  build.spec 含 broken: {"broken" in content}')
    log(f'  build.spec 含 auth_client: {content.count("auth_client")} 处')

# ========== 3. 更新逻辑源码检查 ==========
log('')
log('=' * 60)
log('[18] 更新签名逻辑源码（updater）')
log('=' * 60)
for cand in [r'D:\7tan\7tanAI\tools\security_src\updater.py',
             r'D:\7tan\7tanAI\tools\security_src\updater_src.py',
             r'D:\7tan\7tanAI\src\core\updater.py']:
    if os.path.exists(cand):
        content = open(cand, encoding='utf-8').read()
        log(f'  找到: {cand}')
        # 签名相关
        for kw in ['.sig', 'signature', 'verify', 'RSA', 'public_key', 'sign']:
            c = content.count(kw)
            log(f'    {kw}: {c} 处')
        # 打印签名验证相关行
        for line in content.split('\n'):
            if any(k in line for k in ['.sig', 'signature', 'verify_sign', 'public_key']):
                log(f'    >> {line.strip()}')
        break

# ========== 4. 服务器端更新文件探测 ==========
log('')
log('=' * 60)
log('[19] 服务器更新文件探测 (img.7tan.cn)')
log('=' * 60)
import urllib.request, ssl
ctx = ssl.create_default_context()
for url in ['https://img.7tan.cn/7tan/update/manifest.json',
            'https://img.7tan.cn/7tan/update/7tan-pro-update-v1.0.3.zip',
            'https://img.7tan.cn/7tan/update/7tan-pro-update-v1.0.3.zip.sig',
            'https://img.7tan.cn/7tan/update/latest.json']:
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=8, context=ctx)
        ct = r.headers.get('Content-Type', '')
        cl = r.headers.get('Content-Length', '?')
        log(f'  {url}\n    -> {r.status} {ct} len={cl}')
        r.close()
    except Exception as e:
        log(f'  {url}\n    -> ❌ {type(e).__name__}: {str(e)[:100]}')

# ========== 5. 7tan-editor/data/auth 是否该在发布目录 ==========
log('')
log('=' * 60)
log('[20] 发布目录 data\\auth 运行时文件评估')
log('=' * 60)
for f in ['owner.dat', 'token.dat', 'device_last_report.json']:
    fp = os.path.join(r'D:\7tan\7tanAI\dist\7tan-editor\data\auth', f)
    if os.path.exists(fp):
        sz = os.path.getsize(fp)
        log(f'  {f}: {sz:,} B {"⚠️ 含授权信息" if f == "owner.dat" else "（运行时生成）"}')
