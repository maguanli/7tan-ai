# -*- coding: utf-8 -*-
"""审计第 2 部分：更新包签名 + release zip 净化 + 字符串泄露 + _internal/src"""
import os, re, zipfile, hashlib

log = lambda *a: print(*a)

# ========== 1. 更新包内签名文件 ==========
log('=' * 60)
log('[9] 更新包 v1.0.3 完整结构 + 签名检查')
log('=' * 60)
upd = r'D:\7tan\7tanAI\dist\release\7tan-pro-update-v1.0.3.zip'
z = zipfile.ZipFile(upd)
names = z.namelist()
sigs = [n for n in names if '.sig' in n.lower() or 'signature' in n.lower() or 'sign' in n.lower()]
log(f'  总文件数: {len(names)}')
log(f'  签名文件: {sigs if sigs else "❌ 无!"}')
# 顶层结构
tops = sorted(set(n.split('/')[0] for n in names))
log(f'  顶层目录: {tops}')
# 列出非 _build/data 的文件（核心文件）
core = [n for n in names if n.endswith('.pyd')]
log(f'  pyd 数量: {len(core)}')
for c in core[:30]:
    log(f'    - {c}')
# 敏感检查
sens = [n for n in names if any(p in n.lower() for p in ['.encryption_key', 'games.db', 'costs.json', 'owner.dat', '.bak', 'test_', 'memory.db'])]
log(f'  敏感文件: {sens if sens else "✅ 无"}')
z.close()

# ========== 2. release 三个包净化检查 ==========
log('')
log('=' * 60)
log('[10] release 三个 zip 净化验证')
log('=' * 60)
for f in ['7tan-editor-free-v1.0.3.zip', '7tan-pro-src-v1.0.3.zip']:
    fp = os.path.join(r'D:\7tan\7tanAI\dist\release', f)
    z = zipfile.ZipFile(fp)
    names = z.namelist()
    sens = [n for n in names if any(p in n.lower() for p in
            ['.encryption_key', '.encryption_salt', 'games.db', 'games.db-wal',
             'costs.json', 'owner.dat', 'device_last_report.json', 'auth/token',
             'token.dat', 'memory.db', 'auth.db', '.pyc'])]
    py_clear = [n for n in names if n.endswith('.py') and 'site-packages' not in n and 'dist-info' not in n]
    log(f'  📦 {f}: {len(names)} 文件')
    log(f'     敏感文件: {sens if sens else "✅ 0 个"}')
    log(f'     明文 py(非第三方): {len(py_clear)} 个')
    for p in py_clear[:20]:
        log(f'       - {p}')
    # update 包里 pyd 是否含 sig 旁文件
    z.close()

# ========== 3. exe 字符串泄露 ==========
log('')
log('=' * 60)
log('[11] exe 敏感字符串扫描')
log('=' * 60)
exe = r'D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe'
data = open(exe, 'rb').read()
patterns = [
    (b'api_key', 'api_key'), (b'secret', 'secret'), (b'password', 'password'),
    (b'token', 'token'), (b'BEGIN RSA PRIVATE KEY', 'RSA私钥'), 
    (b'BEGIN PRIVATE KEY', '私钥'), (b'DEEPSEEK_API_KEY', 'DeepSeek key 环境变量'),
    (b'OSS_ACCESS_KEY', 'OSS key 环境变量'), (b'7233cn', '测试账号'),
    (b'123466', '测试密码'), (b'7tan.com', '7tan域名'),
]
for pat, name in patterns:
    cnt = data.count(pat)
    log(f'  {name}: {cnt} 处' + (' ⚠️' if cnt > 0 and name not in ('7tan域名',) else ''))

# ========== 4. pyd 字符串泄露（auth_client / sec_config / rsa_verify）==========
log('')
log('=' * 60)
log('[12] 安全 pyd 字符串泄露扫描')
log('=' * 60)
pyds = {
    'auth_client': r'D:\7tan\7tanAI\dist\7tan-editor\_internal\src\security\auth_client.pyd',
    'sec_config': r'D:\7tan\7tanAI\dist\7tan-editor\_internal\src\security\sec_config.pyd',
    'rsa_verify': r'D:\7tan\7tanAI\dist\7tan-editor\_internal\src\security\rsa_verify.pyd',
    'integrity': r'D:\7tan\7tanAI\dist\7tan-editor\_internal\src\security\integrity.pyd',
}
for name, fp in pyds.items():
    d = open(fp, 'rb').read()
    hits = []
    for pat in [b'BEGIN RSA PRIVATE KEY', b'BEGIN PRIVATE KEY', b'BEGIN PUBLIC KEY',
                b'api_key', b'sk-', b'AKID', b'LTAI', b'password=', b'secret_key']:
        if pat in d:
            hits.append(pat.decode(errors='ignore'))
    log(f'  {name}: {hits if hits else "✅ 无可疑密钥/口令字符串"}')

# ========== 5. _internal\src 清单 ==========
log('')
log('=' * 60)
log('[13] _internal\\src 目录结构（找明文业务 py）')
log('=' * 60)
src_dir = r'D:\7tan\7tanAI\dist\7tan-editor\_internal\src'
if os.path.exists(src_dir):
    for dp, dn, fn in os.walk(src_dir):
        rel = os.path.relpath(dp, src_dir)
        for f in sorted(fn):
            fp = os.path.join(dp, f)
            sz = os.path.getsize(fp)
            kind = '✅' if f.endswith('.pyd') else ('⚠️' if f.endswith('.py') else '·')
            log(f'  {kind} {os.path.join(rel, f)} ({sz:,} B)')
else:
    log('  ❌ _internal\\src 不存在!')

# ========== 6. dist 其他目录 ==========
log('')
log('=' * 60)
log('[14] dist\\_build / _python 概况')
log('=' * 60)
for d in ['_build', '_python']:
    p = os.path.join(r'D:\7tan\7tanAI\dist', d)
    if os.path.exists(p):
        total = 0
        nf = 0
        for dp, dn, fn in os.walk(p):
            for f in fn:
                nf += 1
                total += os.path.getsize(os.path.join(dp, f))
        log(f'  {d}: {nf} 文件, {total:,} B')
        # 看是否有 .py 明文
        pys = []
        for dp, dn, fn in os.walk(p):
            for f in fn:
                if f.endswith('.py') and 'site-packages' not in dp:
                    pys.append(os.path.join(dp, f))
        log(f'     明文 py: {len(pys)} 个（前5: {pys[:5]}）')
    else:
        log(f'  {d}: 不存在')

# ========== 7. config\settings.py 内容 ==========
log('')
log('=' * 60)
log('[15] 明文残留文件内容')
log('=' * 60)
for f in [r'D:\7tan\7tanAI\dist\7tan-editor\_internal\config\settings.py',
          r'D:\7tan\7tanAI\dist\7tan-editor\_internal\config\__init__.py']:
    if os.path.exists(f):
        log(f'  --- {f} ---')
        try:
            log(open(f, encoding='utf-8').read()[:500])
        except Exception as e:
            log(f'  读取失败: {e}')
