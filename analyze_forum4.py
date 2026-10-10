# -*- coding: utf-8 -*-
import json, sys, io, re
from collections import Counter, defaultdict
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
H=[dict(zip(HCOL,r)) for r in hf]

def yr(s):
    m=re.match(r'(\d{4})',str(s or '')); return int(m.group(1)) if m else 0

# 标题关键词扫描
print('====== 情感/恋爱/婚礼/家族类主题 ======')
kws=['婚礼','结婚','恋爱','喜欢','表白','分手','情人节','光棍','爱情','暗恋','生日快乐','生日','家族','派币','红包']
n=0
for d in L.values():
    t=d['ll_biaoti'] or ''
    if any(k in t for k in kws):
        y=yr(d['ll_time2'])
        if 2009<=y<=2015 and int(d['ll_rchf'] or 0)>=10:
            print(f"  id={d['id']:>7} 回{d['ll_rchf']:>4} [{d['ll_time2'][:10]}] {d['ll_name']} | {t[:50]}")
            n+=1
            if n>=60: break

# 早期 2009-2010 主题
print('\n====== 早期（2009-2010）主题样本 ======')
n=0
for d in sorted(L.values(), key=lambda x:x['ll_time2'] or ''):
    y=yr(d['ll_time2'])
    if 2009<=y<=2010:
        print(f"  id={d['id']:>7} [{d['ll_time2'][:10]}] 版{d['ll_idd']} {d['ll_name']} | {(d['ll_biaoti'] or '')[:50]}")
        n+=1
        if n>=40: break
