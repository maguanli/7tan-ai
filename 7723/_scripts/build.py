# -*- coding: utf-8 -*-
"""读取 _dump_*.pkl -> 生成《7723大事记》HTML + Markdown（ID 精确锚定）
用法: python build.py  (先运行 extract.py)"""
import pickle, collections, re, html

OUT = r'D:\7tan\7tanAI\7723\_dump'
LT = pickle.load(open(OUT + '_lt.pkl', 'rb'))
HF = pickle.load(open(OUT + '_hf.pkl', 'rb'))
meta = pickle.load(open(OUT + '_meta.pkl', 'rb'))
ID = {t[0]: t for t in LT}
HFI = collections.defaultdict(list)
for h in HF:
    HFI[h[1]].append(h)


def strip_ubb(t):
    if not t:
        return ''
    t = t.replace('\\r', '\n').replace('\\n', '\n')
    t = re.sub(r'（\s*/?\s*(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply)\b[^）]*）', '', t, flags=re.I)
    t = re.sub(r'\(/?(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply)\b[^)]*\)', '', t, flags=re.I)
    t = re.sub(r'\\\\+', ' ', t); t = re.sub(r'\\+', '', t)
    t = re.sub(r'\s*\n\s*', '\n', t); t = re.sub(r'[ \t]{2,}', ' ', t)
    return t.strip()


def clean1(t, n):
    t = strip_ubb(t).replace('\n', ' ')
    return re.sub(r'\s{2,}', ' ', t).strip()[:n]


# 里程碑：(年份, 事件名, 帖ID)  ★重点补全 2009 / 2010 / 2014 / 2015
MIL = [
    # ---- 2009 建坛元年 ----
    ('2009', '建坛首帖《抗日英雄传之任务攻略》', '154'),
    ('2009', '早期游戏评测《寂静岭》玩后感触', '158'),
    ('2009', '情感板块名帖《女孩，别让爱你的男人太累了》', '170'),
    ('2009', '《谁都别指望，全要靠自己》', '180'),
    ('2009', '早期汉化游戏《火焰之纹章外传·索非亚复苏》', '219'),
    # ---- 2010 ----
    ('2010', '网站首页第一次改版', '498'),
    ('2010', '《7723.cn 因你我的世界不再单调》', '592'),
    ('2010', '《破解网吧收费系统 100% 成功》', '707'),
    ('2010', '《版主十要十不要》', '908'),
    ('2010', '「7723 版主每日签到」开帖', '1043'),
    ('2010', '高考的同学请进', '1151'),
    ('2010', '会员请进', '1282'),
    ('2010', '【活动】资源帖换 QQ 空间人气', '1771'),
    ('2010', '日 PV 突破 50 万', '1826'),
    # ---- 2011 ----
    ('2011', '《新人导航》筑楼', '5470'),
    ('2011', '忠实用户小调查', '5500'),
    ('2011', '首期「你评游戏，我送话费」启动', '5604'),
    ('2011', '遭恶意攻击后恢复访问', '7731'),
    ('2011', '「游戏评论组」活动开锣', '7196'),
    # ---- 2012 ----
    ('2012', '论坛当众表白《雷秋仪，我喜欢你》', '12968'),
    ('2012', '７７２３刷楼大赛', '22498'),
    ('2012', '《７７２３的未来？你怎么看》', '24489'),
    ('2012', '站长的告别信', '28504'),
    ('2012', '严禁在论坛发「我走了」', '39815'),
    # ---- 2013 ----
    ('2013', 'bbs.7723.com 独立运营', '54016'),
    ('2013', '《7723 论坛永不会没落》', '55149'),
    ('2013', '为 7723.com 上线做准备', '55312'),
    ('2013', '7723.com 的 LOGO', '55413'),
    ('2013', '电脑版正式上线', '55970'),
    ('2013', '「游戏评论组」活动再次启动', '56641'),
    ('2013', 'WAP 站彩版', '57169'),
    ('2013', '论坛改革会员讨论', '58419'),
    ('2013', '反思「副站长权力之争」', '58510'),
    ('2013', '《本论坛版主请进》', '58592'),
    ('2013', '活动宣传部成立', '58717'),
    ('2013', '久违的在线人数', '59324'),
    ('2013', '诚招版主', '60320'),
    # ---- 2014 大幅补全 ----
    ('2014', '2014 年盖楼活动（奖品 ID:2014）', '60631'),
    ('2014', '7723 论坛桌面快捷登陆发布', '60956'),
    ('2014', '7723 首页彩版将上线', '61117'),
    ('2014', '7723 下载站彩版正式上线', '61396'),
    ('2014', '【官方】七坛史上最大派币活动', '61490'),
    ('2014', '[讨论] 关于会员金币膨胀的处理方法', '61725'),
    ('2014', '论坛金币转换成金钻币（12 号前执行）', '61998'),
    ('2014', '关于会员币改革滋事捣乱者处理公告', '62119'),
    ('2014', '《Flappy Bird，你过了几关》', '62257'),
    ('2014', '网盘投票', '63249'),
    ('2014', '百度口碑 — 7723 手机游戏网之评论', '64549'),
    ('2014', '[讨论] 传说中的《7723 传》', '65035'),
    ('2014', '「五一」盖楼活动（奖品 ID:3333）', '65129'),
    ('2014', '5252 网址导航已上线', '65362'),
    ('2014', '家族基金已恢复部分基金', '65413'),
    ('2014', '端午派币（599 回复）', '66066'),
    ('2014', '7723 电脑站百度分享达 1000 个', '66280'),
    ('2014', '[公告] 关于游戏名称的整改（剑网行动）', '66576'),
    ('2014', '城堡争霸 7723 官方联盟成立', '67078'),
    ('2014', '「游戏评论组」活动开锣', '67621'),
    ('2014', '7723 上线首款 HTML5 小游戏', '67963'),
    ('2014', '论坛彩版抢先体验', '68417'),
    # ---- 2015 大幅补全 ----
    ('2015', '安卓游戏总下载量 7,472,995 次', '69604'),
    ('2015', '《如果哪一天 7 坛消失了》', '69748'),
    ('2015', '论坛经十几天修复，恢复访问速度', '69851'),
    ('2015', '官方新年活动征求建议', '69951'),
    ('2015', '春节盖楼活动（奖品 ID:7723，2405 回复）', '70161'),
    ('2015', '《告诉大家一个遗憾的消息》——七坛可能要关闭了', '70379'),
]


def nrep(tid):
    return len([h for h in HFI.get(tid, []) if h[5] and h[5][:4] <= '2016'])


def real_replies(tid, k=5):
    rp = [h for h in HFI.get(tid, []) if h[2] and h[5] and h[5][:4] <= '2016']
    return sorted(rp, key=lambda x: x[5])[:k]


items = []
for year, label, tid in MIL:
    t = ID.get(tid)
    if not t:
        print('MISS', label); continue
    items.append({
        'year': year, 'label': label, 'id': t[0], 'date': (t[7] or '')[:10],
        'author': t[3], 'title': strip_ubb(t[5]),
        'content': clean1(t[6], 620), 'nrep': nrep(t[0]),
        'replies': [{'u': h[3], 't': (h[5] or '')[:16], 'x': clean1(h[4], 150)}
                    for h in real_replies(t[0])],
    })

md = ['# 7723(7坛) 大事记（2009—2015）\n',
      '> 依据主站数据库原样整理：主题 54,230 篇 · 回复 412,632 条 · 注册记录 52,755 · 版块 11 个\n']
for it in items:
    md.append('## %s · %s' % (it['date'], it['label']))
    md.append('- 帖主：%s ｜ 回复：%d ｜ 帖号：%s' % (it['author'], it['nrep'], it['id']))
    md.append('- 原帖：《%s》' % it['title'])
    md.append('- 原文：%s' % it['content'])
    for r in it['replies']:
        md.append('  - %s %s：%s' % (r['t'], r['u'], r['x']))
    md.append('')
open(r'D:\7tan\7tanAI\7723\7723大事记.md', 'w', encoding='utf-8').write('\n'.join(md))


def esc(s):
    return html.escape(s or '')


cards, cur = [], None
for it in items:
    if it['year'] != cur:
        cur = it['year']
        cards.append('<div class="yr"><span>%s</span></div>' % esc(cur))
    reps = ''.join('<div class="rep"><b>%s</b><span class="rt">%s</span><span class="rx">%s</span></div>'
                   % (esc(r['u']), esc(r['t'][:10]), esc(r['x'])) for r in it['replies'])
    cards.append('''
    <div class="item"><div class="dot"></div><div class="card">
      <div class="chead"><span class="date">%s</span><span class="board">回复 %d</span></div>
      <h3>%s</h3>
      <div class="meta">原帖《%s》 ｜ 帖主 %s ｜ 帖号 %s</div>
      <div class="content">%s</div>
      <div class="reps">%s</div>
    </div></div>''' % (esc(it['date']), it['nrep'], esc(it['label']),
                       esc(it['title']), esc(it['author']), esc(it['id']),
                       esc(it['content']), reps))

TEMPLATE = open(r'D:\7tan\7tanAI\7723\_scripts\template.html', encoding='utf-8').read()
open(r'D:\7tan\7tanAI\7723\7723大事记.html', 'w', encoding='utf-8').write(
    TEMPLATE.replace('<!--CARDS-->', '\n'.join(cards)))
print('milestones:', len(items))
import collections as _c
print('by year:', sorted(_c.Counter(i['year'] for i in items).items()))
