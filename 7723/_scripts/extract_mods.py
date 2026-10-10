# -*- coding: utf-8 -*-
"""为每位版主提取代表帖（正文+回复），输出 JSON"""
import pickle, json, re, collections

OUT = r'D:\7tan\7tanAI\7723\_dump'
LT = pickle.load(open(OUT + '_lt.pkl', 'rb'))
HF = pickle.load(open(OUT + '_hf.pkl', 'rb'))
HFI = collections.defaultdict(list)
for h in HF:
    HFI[h[1]].append(h)

def strip_ubb(t):
    if not t:
        return ''
    t = t.replace('\\r', '\n').replace('\\n', '\n')
    t = re.sub(r'（\s*/?\s*(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply)\b[^）]*）', '', t, flags=re.I)
    t = re.sub(r'\(/?(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply)\b[^)]*\)', '', t, flags=re.I)
    t = re.sub(r'\[/?(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply)\b[^\]]*\]', '', t, flags=re.I)
    t = re.sub(r'\\+', '', t)
    t = re.sub(r'\s*\n\s*', '\n', t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    return t.strip()

def clean1(t, n):
    t = strip_ubb(t).replace('\n', ' ')
    return re.sub(r'\s{2,}', ' ', t).strip()[:n]

def replies2016(tid):
    rp = [h for h in HFI.get(tid, []) if h[4] and h[5] and h[5][:4] <= '2016']
    return sorted(rp, key=lambda x: x[5])

# 版主：DB作者名 -> 展示名+身份
MODS = [
    (['存我小妖', '存我', '流氓高手@存我'], '存我（存我小妖）', '核心管理 · 首任副站长 · 评论组组长'),
    (['博丽灵梦'], '博丽灵梦', '版主'),
    (['大门'], '大门', '情感文学版版主'),
    (['莫小跳'], '莫小跳', '版主'),
    (['皇甫朝云'], '皇甫朝云', '友友推荐版 / 点播游戏版主（被站长点名表扬）'),
    (['Cry&小殇'], '小殇', '版主'),
    (['蛋定', '扔蛋组@蛋定'], '蛋定（扔蛋组）', '版主'),
    (['沉默是寡言', '综合组@沉默', '沉默'], '沉默（综合组）', '综合组版主'),
    (['Beta2游侠·小基', '小基'], '小基（Beta2游侠）', '聊天灌水版主'),
    (['不义联盟@Silence'], '不义联盟@Silence', '安卓版主'),
    (['吃屎的小太刀'], '吃屎的小太刀', '小说版主'),
    (['BLOOD'], 'BLOOD', '小说版主'),
    (['秋韵物语'], '秋韵物语', 'JAVA 塞班版主'),
    (['那年那月那流殇、'], '那年那月那流殇、', '点播游戏版主'),
    (['缘分、陌生人'], '缘分、陌生人', '点播版 / 猜猜版主'),
    (['灰烬'], '灰烬', '图片版主'),
    (['玉碎@田驰'], '玉碎@田驰', '各版预备版主'),
    (['暖夏@叶繁成花'], '暖夏@叶繁成花', '版主'),
    (['流氓高手@穆清', '穆清'], '穆清（流氓高手）', '版主'),
    (['华夏管家丶莽蛋'], '华夏管家丶莽蛋', '版主'),
    (['月光'], '月光', '版主'),
    (['╰☆倾城℡苏小染'], '苏小染（倾城）', '版主'),
    (['老子只顶触屏！！！！', '老子只顶触屏！！！'], '老子只顶触屏', '新版主'),
    (['兄弟，残刃——想你们'], '残刃', '版主'),
    (['不修'], '不修', '版主'),
    (['易'], '易（浅）', '猜猜看版主'),
    (['-mmm°、咸蛋超人'], '咸蛋超人', '聊天版实习版主 → 勋章申请版'),
    (['凉宫的消失'], '凉宫的消失', '版主（版规/版务）'),
    (['倾城@神月'], '倾城@神月', '版主'),
    (['管理员  清风明月', '清风明月'], '清风明月', '管理员'),
    (['邪、苍２号', '邪、苍'], '邪、苍', '版主'),
    (['___葬忆°'], '葬忆', '版主（申版活跃）'),
]

byauth = collections.defaultdict(list)
for t in LT:
    a = (t[3] or '').strip()
    if a:
        byauth[a].append(t)

result = []
for names, disp, role in MODS:
    pool = []
    for nm in names:
        pool += byauth.get(nm, [])
    # 去重（按 id）
    seen, uniq = set(), []
    for t in pool:
        if t[0] in seen:
            continue
        seen.add(t[0]); uniq.append(t)
    pool = uniq
    cands = []
    for t in pool:
        dt = t[7] or ''
        if dt[:4] > '2016':
            continue
        c = clean1(t[6], 10)
        if len(c) < 8:
            continue
        nr = len(replies2016(t[0]))
        cands.append((nr, len(c), t))
    cands.sort(key=lambda x: (-x[0], -x[1]))
    if not cands:
        result.append({'name': disp, 'role': role, 'found': False,
                       'posts': len(pool)})
        continue
    nr, cl, t = cands[0]
    rps = replies2016(t[0])[:3]
    result.append({
        'name': disp, 'role': role, 'found': True, 'total_posts': len(pool),
        'id': t[0], 'title': strip_ubb(t[5]),
        'date': (t[7] or '')[:10], 'nrep': nr,
        'content': clean1(t[6], 620),
        'replies': [{'u': h[3], 't': (h[5] or '')[:10], 'x': clean1(h[4], 140)} for h in rps],
    })

json.dump(result, open(r'D:\7tan\7tanAI\7723\_scripts\_mods_posts.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

lines = []
for r in result:
    if r['found']:
        lines.append('%-16s [%s] 帖%s《%s》/%s 回复%d 累计%d帖' %
                     (r['name'], r['role'], r['id'], r['title'][:28], r['date'], r['nrep'], r['total_posts']))
    else:
        lines.append('%-16s [%s]  ** 未找到发帖 (pool=%d)' % (r['name'], r['role'], r['posts']))
open(r'D:\7tan\7tanAI\7723\_scripts\_mods_summary.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('mods:', len(result), 'found:', sum(1 for r in result if r['found']))
