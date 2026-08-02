# -*- coding: utf-8 -*-
"""全面防破解审计脚本 - 扫描 dist\7tan-editor"""
import os, re, sys, hashlib

ROOT = r'D:\7tan\7tanAI\dist\7tan-editor'
out = []

def log(s):
    out.append(s)
    print(s)

# 1. _internal 完整文件树
log('=' * 60)
log('[1] _internal 完整文件清单')
log('=' * 60)
for dp, dn, fn in os.walk(os.path.join(ROOT, '_internal')):
    rel = os.path.relpath(dp, ROOT)
    for f in sorted(fn):
        fp = os.path.join(dp, f)
        try:
            sz = os.path.getsize(fp)
        except OSError:
            sz = -1
        log(f'  {os.path.join(rel, f)}  ({sz:,} B)')

# 2. 安全相关 pyd 定位
log('')
log('=' * 60)
log('[2] 安全模块 pyd 定位')
log('=' * 60)
sec_names = ['auth_client', 'entry_auth', 'sec_config', 'license_verify',
             'rsa_verify', 'device_fingerprint', 'updater', 'strings',
             'safe_modify', 'token_store', 'trial_store', 'prompts', 'integrity']
found_sec = {}
for dp, dn, fn in os.walk(ROOT):
    for f in fn:
        fl = f.lower()
        for s in sec_names:
            if fl.startswith(s) and fl.endswith('.pyd'):
                fp = os.path.join(dp, f)
                found_sec.setdefault(s, []).append((fp, os.path.getsize(fp)))
for s in sec_names:
    if s in found_sec:
        for fp, sz in found_sec[s]:
            log(f'  ✅ {s}: {fp} ({sz:,} B)')
    else:
        log(f'  ❌ {s}: 未找到!')

# 3. 敏感文件检查（应被剔除的）
log('')
log('=' * 60)
log('[3] 敏感文件检查（P1-7 应全部剔除）')
log('=' * 60)
sensitive_patterns = ['.encryption_key', '.encryption_salt', 'games.db',
                      'games.db-wal', 'costs.json', 'owner.dat',
                      'device_last_report.json', 'test_', '.bak', '.pyc',
                      'site_credentials', 'memory.db', 'auth.db']
hits = []
for dp, dn, fn in os.walk(ROOT):
    for f in fn:
        fl = f.lower()
        for p in sensitive_patterns:
            if p.lower() in fl:
                hits.append(os.path.join(dp, f))
                break
if hits:
    for h in sorted(hits):
        log(f'  ⚠️  发现: {h}')
else:
    log('  ✅ 未发现任何敏感文件')

# 4. .py 明文残留检查（应无业务源码明文）
log('')
log('=' * 60)
log('[4] .py 明文源码残留检查')
log('=' * 60)
py_hits = []
for dp, dn, fn in os.walk(ROOT):
    for f in fn:
        if f.endswith('.py'):
            py_hits.append(os.path.join(dp, f))
if py_hits:
    for p in py_hits:
        log(f'  ⚠️  明文 py: {p}')
else:
    log('  ✅ 无 .py 明文残留')

# 5. pyd 导出函数验证（PyInit_ 检查 - 用二进制扫描）
log('')
log('=' * 60)
log('[5] pyd 导出函数验证（PyInit_ 扫描）')
log('=' * 60)
for s in sec_names:
    if s in found_sec:
        fp = found_sec[s][0][0]
        try:
            data = open(fp, 'rb').read()
            init_name = f'PyInit_{s}'.encode()
            # 导出表里找
            found = init_name in data
            log(f'  {s}: PyInit_{s} {"✅ 在二进制中" if found else "❌ 缺失!"} ({len(data):,} B)')
        except Exception as e:
            log(f'  {s}: 读取失败 {e}')

# 6. exe 信息
log('')
log('=' * 60)
log('[6] exe 基本信息')
log('=' * 60)
exe = os.path.join(ROOT, '7tan-editor.exe')
if os.path.exists(exe):
    sz = os.path.getsize(exe)
    md5 = hashlib.md5(open(exe, 'rb').read()).hexdigest()
    data = open(exe, 'rb').read()
    log(f'  大小: {sz:,} B')
    log(f'  MD5: {md5}')
    log(f'  PyInstaller 标志: {"✅ 含 (MEI/archive)" if b"MEI" in data or b"pyi" in data.lower() else "❌ 无"}')
    # 版本信息
    ver_match = re.search(rb'1\.0\.\d+', data)
    if ver_match:
        log(f'  版本字符串: {ver_match.group().decode()}')
    # 检查是否包含 pyd 路径
    for s in ['auth_client', 'entry_auth', 'updater']:
        if s.encode() in data:
            log(f'  内嵌模块名: {s} ✅')
    # Authenticode 签名检查
    import subprocess
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command',
            f'(Get-AuthenticodeSignature "{exe}").Status'],
            capture_output=True, text=True, timeout=30)
        sig = r.stdout.strip()
        log(f'  Authenticode 签名状态: {sig}')
    except Exception as e:
        log(f'  签名检查失败: {e}')

# 7. 更新包检查
log('')
log('=' * 60)
log('[7] 更新包 (release) 检查')
log('=' * 60)
rel = r'D:\7tan\7tanAI\dist\release'
if os.path.exists(rel):
    import zipfile
    for f in sorted(os.listdir(rel)):
        fp = os.path.join(rel, f)
        log(f'  📦 {f} ({os.path.getsize(fp):,} B)')
        if f.endswith('.zip') and 'update' in f:
            try:
                z = zipfile.ZipFile(fp)
                names = z.namelist()
                log(f'    包含 {len(names)} 个文件')
                for n in names[:15]:
                    log(f'      - {n}')
                # 签名文件
                sigs = [n for n in names if n.endswith('.sig') or 'sign' in n.lower()]
                if sigs:
                    for s in sigs:
                        log(f'    ✅ 签名文件: {s}')
                else:
                    log(f'    ❌ 无 .sig 签名文件!')
                z.close()
            except Exception as e:
                log(f'    解压失败: {e}')

# 8. logs 检查
log('')
log('=' * 60)
log('[8] logs 目录检查')
log('=' * 60)
logs_dir = os.path.join(ROOT, 'logs')
if os.path.exists(logs_dir):
    for dp, dn, fn in os.walk(logs_dir):
        for f in fn:
            fp = os.path.join(dp, f)
            log(f'  {os.path.relpath(fp, ROOT)} ({os.path.getsize(fp):,} B)')
else:
    log('  ✅ 无 logs 目录')

with open(r'D:\7tan\7tanAI\_audit_result.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('\n审计完成，结果已保存 _audit_result.txt')
