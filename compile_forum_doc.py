# -*- coding: utf-8 -*-
import json, sys, io, re
from collections import defaultdict, Counter
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
reps=defaultdict(list)
for r in hf:
    d=dict(zip(HCOL,r)); reps[d['ll_id']].append(d)

def clean(t):
    if not t: return ''
    t=re.sub(r'（url＝[^）]*）|（/url）','',t)
    t=re.sub(r'\[[^\]]{0,20}\]','',t)
    t=t.replace('\\r\\n','\n').replace('\\n','\n').replace('\\\\','\n')
    t=re.sub(r'[ \t]+\n','\n',t); t=re.sub(r'\n{3,}','\n\n',t)
    return t.strip()

def yr(s):
    m=re.match(r'(\d{4})',str(s or '')); return m.group(1) if m else '?'

out=[]; w=out.append
w('# ７７２３（7坛）当年的论坛场景与故事 —— 主站数据库考证')
w('> 数据来源：D:\\7tan\\7tan_cn_20260515_090725.sql（7tan.com 主站数据库）')
w('> 表：ll_lt（主题 %d 条）、ll_lthf（回复 %d 条）'%(len(L), len(hf)))
w('')

yc=Counter(yr(d['ll_time2']) for d in L.values())
w('## 一、论坛活跃年份分布（主题数）')
for k in sorted(yc): w(f'- {k} 年：{yc[k]} 条')
w('')

w('## 二、站长「老马(站长)」在论坛的发言（原文精选）')
for d in sorted(L.values(), key=lambda x:x['ll_time2'] or ''):
    if d['ll_name'] and '老马' in d['ll_name']:
        body=clean(d['ll_text'])
        if len(body)>60 and int(d['ll_rchf'] or 0)>=2:
            w(f"### 【{d['ll_biaoti']}】（{d['ll_time2'][:10]} 阅{d['ll_rc']} 回{d['ll_rchf']}）")
            w('> '+body[:700].replace('\n','\n> '))
            w('')

w('## 三、当年的版主/管理团队（从帖子考证）')
w('- 清风明月（管理员）：《今天素WO月下的生日！求祝福！》发帖人，ID对应管理员')
w('- 存我（存我小妖，ID5）：核心管理，《７７２３评论组》家族族长、评论活动组长客服，2013-01 首任副站长')
w('- 月下（ID97/9753）：管理员/活动副组长')
w('- 大门（情感版）、博丽灵梦（小说版）、Beta2游侠·小基（聊天灌水）、不义联盟@Silence（安卓版）、吃屎的小太刀/BLOOD（小说版）、秋韵物语（JAVA塞班）、皇甫朝云（友友推荐版、点播游戏版，被站长点名表扬）')
w('')

w('## 四、每月「游戏评论组」活动（老马亲自主持·送话费/Q币）')
for d in sorted(L.values(), key=lambda x:x['ll_time2'] or ''):
    if '游戏评论组' in (d['ll_biaoti'] or '') or '游戏评论' in (d['ll_biaoti'] or ''):
        w(f"- 【{d['ll_biaoti']}】（{d['ll_time2'][:10]} 回{d['ll_rchf']}）作者：{d['ll_name']}")
w('')
# 一场活动的完整说明
d=L.get('13464')
if d:
    w('### 活动范例：3月份活动开锣（原文，由336网址大全赞助）')
    w('> '+clean(d['ll_text'])[:1500].replace('\n','\n> '))
    w('')
    w('### 网友报名（"我要参加！"）节选：')
    rs=sorted(reps.get('13464',[]), key=lambda x:x['ll_time'] or '')
    for r in rs[:25]:
        t=clean(r['ll_text'])
        if t: w(f"- {r['ll_name']}：{t[:40]}")
    w('')

w('## 五、社区的"走走风"——离别与挽留（原文精选）')
for tid in [21573,28504,21477,39815,55149]:
    d=L.get(str(tid))
    if not d: continue
    w(f"### 【{d['ll_biaoti']}】（{d['ll_time2'][:10]} 回{d['ll_rchf']}）作者：{d['ll_name']}")
    w('> '+clean(d['ll_text'])[:800].replace('\n','\n> '))
    rs=sorted(reps.get(str(tid),[]), key=lambda x:x['ll_time'] or '')
    for r in rs[:12]:
        t=clean(r['ll_text'])
        if t: w(f"- {r['ll_name']}：{t[:100]}")
    w('')

w('## 六、家族文化（网友自组织）')
for d in L.values():
    t=d['ll_biaoti'] or ''
    if '家族' in t and int(d['ll_rchf'] or 0)>=10:
        w(f"- 【{t}】（{d['ll_time2'][:10]} 回{d['ll_rchf']}）{d['ll_name']}")
w('')

w('## 七、网友之间的感情·爱情与表白')
for tid in [14892,12968,12621,22235]:
    d=L.get(str(tid))
    if not d: continue
    w(f"### 【{d['ll_biaoti']}】（{d['ll_time2'][:10]} 回{d['ll_rchf']}）{d['ll_name']}")
    w('> '+clean(d['ll_text'])[:400].replace('\n','\n> '))
    rs=sorted(reps.get(str(tid),[]), key=lambda x:x['ll_time'] or '')
    for r in rs[:10]:
        t=clean(r['ll_text'])
        if t: w(f"- {r['ll_name']}：{t[:90]}")
    w('')

w('## 八、最活跃网友榜（2009-2015·按发帖数）')
c=Counter(d['ll_name'] for d in L.values() if d['ll_name'] and '2009'<=yr(d['ll_time2'])<='2015')
w('| 排名 | 网名 | 主题数 |')
w('|---|---|---|')
for i,(n,cnt) in enumerate(c.most_common(30),1):
    w(f'| {i} | {n} | {cnt} |')
w('')

doc='\n'.join(out)
open(r'D:\7tan\7tanAI\7723\7723当年论坛场景与故事（主站数据库考证）.md','w',encoding='utf-8').write(doc)
print('written chars', len(doc))
print('lines', doc.count(chr(10)))
