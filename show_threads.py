# -*- coding: utf-8 -*-
import json, sys, io, re
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

lt=json.load(open(r'D:\7tan\7tanAI\_ll_lt.json',encoding='utf-8'))
hf=json.load(open(r'D:\7tan\7tanAI\_ll_lthf.json',encoding='utf-8'))
COLS=['id','ll_idd','ll_useid','ll_name','ll_or','ll_biaoti','ll_text','ll_textb','ll_url',
'll_toupao','ll_rcx','ll_rcd','ll_rc','ll_rchf','ll_jh','ll_lock','ll_hide','ll_shangxian',
'll_retime','ll_time1','ll_time2','ll_over','ll_zt','ll_furl','ll_yy','ll_mb','ll_pb','ll_xx',
'll_status','ll_ding','ll_jing','ll_tongji','ll_pj','ll_zan']
L={}
for r in lt:
    d=dict(zip(COLS,r)); L[d['id']]=d
HCOL=['id','ll_id','ll_idd','ll_useid','ll_father_id','ll_zan','ll_name','ll_text','ll_file','ll_time','ll_face','upsize_ts','ll_time2','ll_furl','ll_yy','ll_xx','lt_superb','ll_ai','ll_pj','ll_ding']
H=[]
for r in hf:
    H.append(dict(zip(HCOL,r)))
# 按 ll_id 分组回复
from collections import defaultdict
reps=defaultdict(list)
for d in H:
    reps[d['ll_id']].append(d)

def clean(t):
    if not t: return ''
    t=re.sub(r'\[[^\]]{0,20}\]','',t)  # BBCode
    t=re.sub(r'（img）.*?（/img）','',t)
    t=t.replace('\\\\','\n').replace('\\r\\n','\n')
    t=re.sub(r'\n{3,}','\n\n',t)
    return t.strip()

def show(tid, maxrep=12):
    d=L.get(str(tid))
    if not d:
        print(f'[thread {tid} not found]'); return
    print('='*70)
    print(f"【{d['ll_biaoti']}】")
    print(f"  作者: {d['ll_name']}  时间:{d['ll_time2']}  阅{d['ll_rc']} 回{d['ll_rchf']} 版{d['ll_idd']}")
    print('  正文:', clean(d['ll_text'])[:1200])
    rs=sorted(reps.get(str(tid),[]), key=lambda x:x['ll_time'] or '')
    print(f"  --- 回复 {len(rs)} 条（取前{maxrep}） ---")
    for r in rs[:maxrep]:
        tx=clean(r['ll_text'])
        if not tx: continue
        print(f"    [{r['ll_time'][:10] if r['ll_time'] else '?'}] {r['ll_name']}: {tx[:150]}")

for tid in [28504,54918,13261,21477,21573,39815,55149,13235,11348,47489,43023]:
    show(tid, 15)
