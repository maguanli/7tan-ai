# -*- coding: utf-8 -*-
import pickle, json, re, collections
OUT = r'D:\7tan\7tanAI\7723\_dump'
LT = pickle.load(open(OUT + '_lt.pkl', 'rb'))
HF = pickle.load(open(OUT + '_hf.pkl', 'rb'))
HFI = collections.defaultdict(list)
for h in HF:
    HFI[h[1]].append(h)
exec(open(r'D:\7tan\7tanAI\7723\_scripts\extract_mods.py', encoding='utf-8').read().split('result = []')[0].split('MODS = [')[0])

def strip_ubb(t):
    if not t:
        return ''
    t = t.replace('\\r', '\n').replace('\\n', '\n')
    t = re.sub(r'（\s*/?\s*(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply)\b[^）]*）', '', t, flags=re.I)
    t = re.sub(r'\(/?(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply)\b[^)]*\)', '', t, flags=re.I)
    t = re.sub(r'\[/?(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply)\b[^\]]*\]', '', t, flags=re.I)
    t = re.sub(r'\\+', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def replies2016(tid):
    return [h for h in HFI.get(tid, []) if h[4] and h[5] and h[5][:4] <= '2016']

MODS = [
    (['存我小妖', '存我', '流氓高手@存我'], '存我（存我小妖）'),
    (['博丽灵梦'], '博丽灵梦'),
    (['大门'], '大门'),
    (['莫小跳'], '莫小跳'),
    (['皇甫朝云'], '皇甫朝云'),
    (['Cry&小殇'], '小殇'),
    (['蛋定', '扔蛋组@蛋定'], '蛋定'),
    (['沉默是寡言', '综合组@沉默', '沉默'], '沉默'),
    (['Beta2游侠·小基', '小基'], '小基'),
    (['不义联盟@Silence'], '不义联盟@Silence'),
    (['吃屎的小太刀'], '吃屎的小太刀'),
    (['BLOOD'], 'BLOOD'),
    (['秋韵物语'], '秋韵物语'),
    (['那年那月那流殇、'], '那年那月那流殇、'),
    (['缘分、陌生人'], '缘分、陌生人'),
    (['灰烬'], '灰烬'),
    (['玉碎@田驰'], '玉碎@田驰'),
    (['暖夏@叶繁成花'], '暖夏@叶繁成花'),
    (['流氓高手@穆清', '穆清'], '穆清'),
    (['华夏管家丶莽蛋'], '华夏管家丶莽蛋'),
    (['月光'], '月光'),
    (['╰☆倾城℡苏小染'], '苏小染'),
    (['老子只顶触屏！！！！', '老子只顶触屏！！！'], '老子只顶触屏'),
    (['兄弟，残刃——想你们'], '残刃'),
    (['不修'], '不修'),
    (['易'], '易（浅）'),
    (['-mmm°、咸蛋超人'], '咸蛋超人'),
    (['凉宫的消失'], '凉宫的消失'),
    (['倾城@神月'], '倾城@神月'),
    (['管理员  清风明月', '清风明月'], '清风明月'),
    (['邪、苍２号', '邪、苍'], '邪、苍'),
    (['___葬忆°'], '葬忆'),
]
byauth = collections.defaultdict(list)
for t in LT:
    a = (t[3] or '').strip()
    if a:
        byauth[a].append(t)

out = []
for names, disp in MODS:
    pool = []
    for nm in names:
        pool += byauth.get(nm, [])
    seen, uniq = set(), []
    for t in pool:
        if t[0] in seen:
            continue
        seen.add(t[0]); uniq.append(t)
    cands = []
    for t in uniq:
        if (t[7] or '')[:4] > '2016':
            continue
        c = strip_ubb(t[6])
        if len(c) < 20:
            continue
        cands.append((len(replies2016(t[0])), len(c), t, c))
    cands.sort(key=lambda x: (-x[0], -x[1]))
    out.append('########## %s ##########' % disp)
    for nr, cl, t, c in cands[:8]:
        out.append('[%s|%s] 回复%d 正文%d字 《%s》' % (t[0], (t[7] or '')[:10], nr, cl, strip_ubb(t[5])[:40]))
        out.append('    ' + c[:90])
    out.append('')
open(r'D:\7tan\7tanAI\7723\_scripts\_cands.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('ok', len(out))
