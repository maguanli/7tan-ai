# -*- coding: utf-8 -*-
"""
本轮（重打包后）部署：只做上传与清单同步，不做 git push。
原因：远端是真实仓库（1.75GB，含 3 个 >100MB 的 mp4），全量 push 必失败。
GitHub 侧的发布包更新由 tools/gh_release.py 单独处理。
"""
import importlib.util
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TOOLS = r'D:\7tan\7tanAI\tools\deploy_v1023.py'

spec = importlib.util.spec_from_file_location('deploy_v1023', TOOLS)
dv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dv)

dv.log('重打包后部署开始  %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
dv.log('本次跳过 git push（真实仓库 1.75GB，>100MB 文件必被拒）')

TASKS_A = [
    ('上传编辑器包 400MB', dv.t_upload_editor),
    ('上传网页包 58MB', dv.t_upload_web),
]
ra = dv.run_stage('A(上传)', TASKS_A)
if not all(r['ok'] for r in ra):
    dv.log('!! 阶段 A 有失败，中止（不更新清单）')
    for r in ra:
        if not r['ok']:
            dv.log('   FAIL %s: %s' % (r['title'], r['msg']))
    sys.exit(1)

rb = dv.run_stage('B(清单/995/兜底)', dv.TASKS_B)

dv.log('')
dv.log('=' * 66)
dv.log('结果汇总')
dv.log('=' * 66)
bad = 0
for r in ra + rb:
    dv.log('  [%s] %-24s %6.1fs  %s' % ('OK  ' if r['ok'] else 'FAIL', r['title'],
                                        r['end'] - r['start'], r['msg'][:280]))
    if not r['ok']:
        bad += 1
dv.log('')
dv.log('PASS %d / FAIL %d' % (len(ra + rb) - bad, bad))
sys.exit(0 if bad == 0 else 1)
