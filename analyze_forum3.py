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
L=[dict(zip(COLS,r)) for r in lt]
HCOL=['id','ll_id','ll_idd','ll_useid','ll_father_id','ll_zan','ll_name','ll_text','ll_file','ll_time','ll_face','upsize_ts','ll_time2','ll_furl','ll_yy','ll_xx','lt_superb','ll_ai','ll_pj','ll_ding']
H=[dict(zip(HCOL,r)) for r in hf]
byid={d['id']:d for d in L}

# 老马(站长) 发的所有主题
print('====== 老马(站长) 发布的主题 ======')
for d in L:
    if d['ll_name'] and ('站长' in d['ll_name'] or d['ll_name'].strip()=='老马'):
        print(f"  id={d['id']:>7} 回{d['ll_rchf']:>5} 阅{d['ll_rc']:>7} [{d['ll_time2'][:10]}] {d['ll_biaoti']}")

# 标题含关键词的主题
def find_title(kw, ymin=2009, ymax=2015):
    print(f'\n====== 标题含"{kw}" ======')
    n=0
    for d in L:
        if d['ll_biaoti'] and kw in d['ll_biaoti']:
            y=int((d['ll_time2'] or '0')[:4] or 0)
            if ymin<=y<=ymax:
                print(f"  id={d['id']:>7} 回{d['ll_rchf']:>4} [{d['ll_time2'][:10]}] {d['ll_name']} | {d['ll_biaoti'][:60]}")
                n+=1
                if n>=40: break

for kw in ['版主','站长','活动','公告','告别','离开','站庆','签到','奖励','招聘']:
    find_title(kw)
