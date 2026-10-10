# -*- coding: utf-8 -*-
import json, sys, io, re
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

lt=json.load(open(r'D:\7tan\7tanAI\_ll_lt.json',encoding='utf-8'))
hf=json.load(open(r'D:\7tan\7tanAI\_ll_lthf.json',encoding='utf-8'))

# ll_lt 列
COLS=['id','ll_idd','ll_useid','ll_name','ll_or','ll_biaoti','ll_text','ll_textb','ll_url',
'll_toupao','ll_rcx','ll_rcd','ll_rc','ll_rchf','ll_jh','ll_lock','ll_hide','ll_shangxian',
'll_retime','ll_time1','ll_time2','ll_over','ll_zt','ll_furl','ll_yy','ll_mb','ll_pb','ll_xx',
'll_status','ll_ding','ll_jing','ll_tongji','ll_pj','ll_zan']
print('ll_lt rows', len(lt), 'cols expect', len(COLS))
print('sample row0 len', len(lt[0]))
print('row0:', dict(zip(COLS, lt[0])))

HCOL=['id','ll_id','ll_idd','ll_useid','ll_father_id','ll_zan','ll_name','ll_text','ll_file','ll_time','ll_face','upsize_ts','ll_time2','ll_furl','ll_yy','ll_xx','lt_superb','ll_ai','ll_pj','ll_ding']
print('\nhf row0 len', len(hf[0]))
print('hf row0:', dict(zip(HCOL, hf[0])))

# 年份分布
def year(s):
    if not s: return None
    m=re.match(r'(\d{4})', str(s))
    return m.group(1) if m else None
yc=Counter()
for r in lt:
    d=dict(zip(COLS,r))
    y=year(d.get('ll_time2') or d.get('ll_retime') or d.get('ll_time1'))
    yc[y]+=1
print('\n主题年份分布:', dict(sorted(yc.items(), key=lambda x:(x[0] or ''))))

yhc=Counter()
for r in hf:
    d=dict(zip(HCOL,r))
    y=year(d.get('ll_time') or d.get('ll_time2'))
    yhc[y]+=1
print('回复年份分布:', dict(sorted(yhc.items(), key=lambda x:(x[0] or ''))))
