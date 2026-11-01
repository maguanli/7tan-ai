# -*- coding: utf-8 -*-
"""
v1.0.23 发布：多任务并发部署
阶段 A（3 路并行）：GitHub 推送 / 上传编辑器包 / 上传网页包
阶段 B（3 路并行）：更新清单 / 更新 995 词条 / 更新下载页兜底值
依赖说明：B 依赖 A 的包已落地，避免"清单已指新包但文件没到"
"""
import json, os, subprocess, sys, threading, time, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(r'D:\7tan\7tanAI')
SRV = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))['server']
PHP = r'D:\php\php-8.2.27\php.exe'
UPDATES = 'D:/workspace/7tan/updates'
APPSIZE = 419870044
VER = '1.0.23'

LOG_LOCK = threading.Lock()
def log(msg):
    with LOG_LOCK:
        print(msg, flush=True)

def conn():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SRV['host'], SRV['port'], SRV['user'], SRV['password'],
                timeout=30, look_for_keys=False, allow_agent=False)
    return ssh

def run_php_remote(ssh, local_php, timeout=300):
    sftp = ssh.open_sftp()
    remote = UPDATES + '/_deploy_' + local_php.name
    sftp.put(str(local_php), remote)
    _i, o, e = ssh.exec_command('"%s" "%s"' % (PHP, remote), timeout=timeout)
    out = o.read().decode('utf-8', 'ignore')
    err = e.read().decode('utf-8', 'ignore')
    try: sftp.remove(remote)
    except Exception: pass
    sftp.close()
    return out, err

# ---------------- 任务实现 ----------------

def t_git_push():
    """提交并推送当前分支到 GitHub"""
    def g(*a, timeout=600):
        p = subprocess.run(['git'] + list(a), cwd=str(ROOT), capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=timeout)
        return p.returncode, (p.stdout or '') + (p.stderr or '')

    rc, out = g('add', '-A')
    if rc != 0:
        return {'ok': False, 'msg': 'git add 失败: ' + out[-400:]}

    rc, out = g('diff', '--cached', '--quiet')
    committed = False
    if rc != 0:  # 有变更
        rc2, o2 = g('commit', '-m', 'chore(release): v1.0.23 发布包与更新清单')
        committed = (rc2 == 0)
        if not committed:
            return {'ok': False, 'msg': 'commit 失败: ' + o2[-400:]}

    rc, out = g('push', 'origin', 'HEAD', timeout=900)
    ok = (rc == 0)
    return {'ok': ok,
            'msg': ('committed=%s; ' % committed) + out.strip()[-500:]}

def _upload_pair(local_zip, local_sig):
    """上传 zip + sig，返回耗时与校验结果"""
    size = local_zip.stat().st_size
    t0 = time.time()
    ssh = conn()
    sftp = ssh.open_sftp()
    last = [0.0]
    def cb(done, total):
        now = time.time()
        if now - last[0] > 8 or done >= total:
            last[0] = now
            pct = done * 100.0 / total if total else 0
            mb = done / 1048576.0
            log('      %-34s %5.1f%%  %7.1f MB  %.0fs' % (local_zip.name[:34], pct, mb, now - t0))
    sftp.put(str(local_zip), UPDATES + '/' + local_zip.name, callback=cb)
    sftp.put(str(local_sig), UPDATES + '/' + local_sig.name)

    # 远端校验：大小 + md5
    def md5_local(p):
        h = hashlib.md5()
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(4 << 20), b''):
                h.update(chunk)
        return h.hexdigest()
    lm = md5_local(local_zip)
    cmd = '"%s" -r "echo filesize(\'%s/%s\');"' % (PHP, UPDATES, local_zip.name)
    _i, o, e = ssh.exec_command(cmd, timeout=120)
    rsize = o.read().decode('utf-8', 'ignore').strip()
    cmd2 = '"%s" -r "echo md5_file(\'%s/%s\');"' % (PHP, UPDATES, local_zip.name)
    _i, o2, e2 = ssh.exec_command(cmd2, timeout=300)
    rmd5 = o2.read().decode('utf-8', 'ignore').strip()

    ok = (str(size) == rsize) and (lm == rmd5)
    sftp.close(); ssh.close()
    return {'ok': ok,
            'msg': 'local=%d remote=%s md5=%s %s' % (size, rsize, rmd5[:16], 'MATCH' if ok else 'MISMATCH'),
            'dur': time.time() - t0}

def t_upload_editor():
    return _upload_pair(ROOT / 'dist' / 'release' / ('7tan-editor-free-v%s.zip' % VER),
                        ROOT / 'dist' / 'release' / ('7tan-editor-free-v%s.zip.sig' % VER))

def t_upload_web():
    return _upload_pair(ROOT / 'dist' / 'release' / ('7tan-web-v%s.zip' % VER),
                        ROOT / 'dist' / 'release' / ('7tan-web-v%s.zip.sig' % VER))

def t_upload_manifest():
    """version.json + index.html"""
    ssh = conn()
    sftp = ssh.open_sftp()
    files = [
        (ROOT / 'website' / 'updates' / 'version.json', UPDATES + '/version.json'),
        (ROOT / 'website' / 'updates' / 'index.html', UPDATES + '/index.html'),
    ]
    res = []
    for lp, rp in files:
        sftp.put(str(lp), rp)
        st = sftp.stat(rp)
        res.append('%s %d B %s' % (lp.name, st.st_size,
                                    'OK' if st.st_size == lp.stat().st_size else 'MISMATCH'))
    sftp.close(); ssh.close()
    return {'ok': all('OK' in r for r in res), 'msg': '; '.join(res)}

def t_update_995():
    """更新 995 词条：版本/大小/下载地址/更新说明/百科"""
    body_file = ROOT / 'data' / '_995_new_body.txt'
    newbody = body_file.read_text(encoding='utf-8')

    lines = [
        'v1.0.23 更新：上线全新 Agent 架构，AI 开始指挥 AI 干活——新增子 Agent 派工（独立会话、独立预算、代码类任务自动分配 git worktree）；多任务并发与资源隔离（中止信号按作用域隔离、资源租约、每 Worker 独立浏览器视图）；发布验收断言闸门（故障即判失败）；命令作用域围栏与全量审计。修复超长历史消息导致调用失败。'
    ]
    gxts = lines[0]
    lead = '1.0.23 官方词条：软件与插件完全免费，Windows 10／11 解压即用；AI 能力需自备 API 密钥。'

    ssh = conn()
    sftp = ssh.open_sftp()
    # 上传新 body 与更新脚本
    tmp_body = UPDATES + '/_995_new_body.txt'
    sftp.put(str(body_file), tmp_body)

    php_src = '''<?php
require 'D:/workspace/7tan/db.php';
$db = getDB();
$body = file_get_contents('D:/workspace/7tan/updates/_995_new_body.txt');
if ($body === false || strlen($body) < 1000) { echo "BODY_READ_FAIL\\n"; exit(1); }
$gxts = %s;
$lead = %s;
$sql = "UPDATE ll_wadyx SET ll_banben=?, ll_daxiao=?, ll_text=?, ll_gxts=?, ll_baike_ver=?, ll_baike_lead=?, ll_baike_body=?, ll_baike_time=?, ll_retime=? WHERE id=995";
$st = $db->prepare($sql);
$st->execute(array(%s, %d, %s, $gxts, %s, $lead, $body, date('Y-m-d H:i:s'), date('Y-m-d H:i:s')));
echo "AFFECTED=" . $st->rowCount() . "\\n";
$r = $db->query("SELECT ll_banben,ll_daxiao,ll_text,ll_gxts,ll_baike_ver,LEFT(ll_baike_lead,30) lead, LENGTH(ll_baike_body) blen FROM ll_wadyx WHERE id=995")->fetch(PDO::FETCH_ASSOC);
foreach ($r as $k=>$v) { echo "$k = $v\\n"; }
''' % (
        "'" + gxts.replace("'", "\\'") + "'",
        "'" + lead.replace("'", "\\'") + "'",
        "'" + VER + "'",
        APPSIZE,
        "'https://www.7tan.com/updates/7tan-editor-free-v%s.zip'" % VER,
        "'" + VER + "'",
    )
    tmp_php = ROOT / 'data' / '_995_update.php'
    tmp_php.write_text(php_src, encoding='utf-8')
    out, err = run_php_remote(ssh, tmp_php, timeout=180)

    # 清理
    try: sftp.remove(tmp_body)
    except Exception: pass
    sftp.close(); ssh.close()

    ok = ('AFFECTED=1' in out) and ('ll_banben = %s' % VER in out)
    return {'ok': ok, 'msg': (out.strip() + (' | ERR:' + err[:200] if err.strip() else ''))[:500]}

def t_update_aitool():
    """更新 /ai-tool/ 下载页的兜底版本号（读 version.json 失败时用）"""
    ssh = conn()
    sftp = ssh.open_sftp()
    remote = 'D:/workspace/7tan/ai-tool/index.php'
    # 先取远端 md5，确认没被别人改过
    cmd = '"%s" -r "echo md5_file(\'%s\');"' % (PHP, remote)
    _i, o, e = ssh.exec_command(cmd, timeout=120)
    remote_md5 = o.read().decode('utf-8', 'ignore').strip()

    local_copy = ROOT / 'data' / '_aitool_index.php'
    local_md5 = hashlib.md5(local_copy.read_bytes()).hexdigest()
    if remote_md5 != local_md5:
        sftp.close(); ssh.close()
        return {'ok': False,
                'msg': '远端已变动（remote=%s local=%s），跳过以免覆盖' % (remote_md5[:12], local_md5[:12])}

    txt = local_copy.read_text(encoding='utf-8')
    orig = txt
    txt = txt.replace("'version' => '1.0.22'", "'version' => '%s'" % VER)
    txt = txt.replace('/updates/7tan-editor-free-v1.0.22.zip',
                      '/updates/7tan-editor-free-v%s.zip' % VER)
    txt = txt.replace("'size'    => 422663043", "'size'    => %d" % APPSIZE)
    txt = txt.replace("'date'    => '2026-09-13'", "'date'    => '2026-11-01'")
    changed = (txt != orig)
    if not changed:
        sftp.close(); ssh.close()
        return {'ok': True, 'msg': '无需修改（已是新版）'}

    tmp = ROOT / 'data' / '_aitool_index_new.php'
    tmp.write_text(txt, encoding='utf-8')
    sftp.put(str(tmp), remote)
    st = sftp.stat(remote)
    ok = (st.st_size == tmp.stat().st_size)
    sftp.close(); ssh.close()
    return {'ok': ok, 'msg': '已更新兜底值 size=%d 字节' % st.st_size}

# ---------------- 调度 ----------------

TASKS_A = [('GitHub 推送', t_git_push), ('上传编辑器包 400MB', t_upload_editor), ('上传网页包 58MB', t_upload_web)]
TASKS_B = [('更新清单 version.json', t_upload_manifest), ('更新 995 词条', t_update_995), ('更新 /ai-tool/ 兜底', t_update_aitool)]

timeline = []

def run_stage(name, tasks, max_workers=3):
    log('\n' + '=' * 66)
    log('阶段 %s：%d 个任务并发启动' % (name, len(tasks)))
    log('=' * 66)
    t_stage = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {}
        for title, fn in tasks:
            t0 = time.time()
            futs[ex.submit(fn)] = (title, t0)
        for fut in as_completed(futs):
            title, t0 = futs[fut]
            try:
                r = fut.result()
            except Exception as ex_:
                r = {'ok': False, 'msg': '异常: %r' % (ex_,)}
            r['title'] = title
            r['start'] = t0
            r['end'] = time.time()
            results.append(r)
            tl = r['end'] - r['start']
            timeline.append((name, title, t0, r['end'], r['ok']))
            log('  [%s] %-24s %6.1fs  %s' % ('OK  ' if r['ok'] else 'FAIL', title, tl, r['msg'][:300]))
    log('阶段 %s 总耗时 %.1fs' % (name, time.time() - t_stage))
    return results

def main():
    log('v1.0.23 部署开始  %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    ra = run_stage('A', TASKS_A)
    if not all(r['ok'] for r in ra):
        log('\n!! 阶段 A 有失败，中止（不更新清单，避免指向不存在的包）')
        for r in ra:
            if not r['ok']:
                log('   FAIL %s: %s' % (r['title'], r['msg']))
        return 1
    rb = run_stage('B', TASKS_B)

    log('\n' + '=' * 66)
    log('时间线（秒，相对部署开始）')
    log('=' * 66)
    t_base = min(x[2] for x in timeline)
    for stage, title, t0, t1, ok in sorted(timeline, key=lambda x: x[2]):
        bar_s = int(t0 - t_base)
        bar_e = int(t1 - t_base)
        log('  %s %-26s %5.1f -> %5.1f  (%4.1fs)  %s' % (
            stage, title, t0 - t_base, t1 - t_base, t1 - t0,
            '#' * max(1, bar_e - bar_s)))

    total = max(x[3] for x in timeline) - t_base
    serial = sum(x[3] - x[2] for x in timeline)
    log('\n总耗时 %.1fs；串行执行需 %.1fs；节省 %.1fs（%.0f%%）' % (
        total, serial, serial - total, (serial - total) / serial * 100 if serial else 0))
    return 0 if all(r['ok'] for r in ra + rb) else 1

if __name__ == '__main__':
    sys.exit(main())
