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

def yr(s):
    m=re.match(r'(\d{4})', str(s or ''))
    return int(m.group(1)) if m else 0

# 1. 热门主题（按回复数 / 阅读数）2009-2015
old=[d for d in L if 2009<=yr(d['ll_time2'])<=2015]
old.sort(key=lambda d: int(d['ll_rc'] or 0), reverse=True)
print('====== 老论坛 热门主题 TOP20（按阅读量）======')
for d in old[:20]:
    print(f"[{d['ll_time2'][:10]}] 阅{d['ll_rc']} 回{d['ll_rchf']} 版{d['ll_idd']} | {d['ll_name']} | {d['ll_biaoti']}")

# 2. 发帖最多的网友
c=Counter(d['ll_name'] for d in old if d['ll_name'])
print('\n====== 当年发帖最多的网友 TOP30 ======')
for name,n in c.most_common(30):
    print(f'{n:5d}  {name}')

# 3. 回复最多的网友
ch=Counter(d['ll_name'] for d in H if d['ll_name'] and 2009<=yr(d['ll_time'])<=2015)
print('\n====== 当年回帖最多的网友 TOP30 ======')
for name,n in ch.most_common(30):
    print(f'{n:5d}  {name}')
