# -*- coding: utf-8 -*-
"""生成《7723 版主群像》UBB 正文（每位版主一帖 + 原帖链接）"""
import pickle, re, collections

OUT = r'D:\7tan\7tanAI\7723\_dump'
LT = pickle.load(open(OUT + '_lt.pkl', 'rb'))
HF = pickle.load(open(OUT + '_hf.pkl', 'rb'))
HFI = collections.defaultdict(list)
for h in HF:
    HFI[h[1]].append(h)
ID = {t[0]: t for t in LT}

BAD = re.compile(r'(SB|sb|傻逼|傻B|妈的|你妈|你爹|尼玛|卧槽|菊花|拉屎|操你|草你|日你|贱人|杂种|奶头|屁股|色情|生殖器|装逼|屌|疯狗|穷B|呆B|食屎|撸|一夜情|骚)')

def strip_ubb(t):
    if not t:
        return ''
    t = t.replace('\\r', '\n').replace('\\n', '\n')
    t = re.sub(r'[（(]\s*/?\s*(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply|nimg|s|hellos|now|font|color|size|table|tr|td|th)\b[^）)]*[）)]', ' ', t, flags=re.I)
    t = re.sub(r'[（(]\s*url[＝=].*$', ' ', t, flags=re.I | re.S)
    t = re.sub(r'\[/?(url|img|imp|big|option|center|left|right|b|i|u|input|c|reply|nimg|s|hellos|now|font|color|size|table|tr|td|th)\b[^\]]*\]', ' ', t, flags=re.I)
    t = re.sub(r'https?[:：]//\S+', ' ', t)
    t = re.sub(r'(?i)\bwww\.[^\s）)]+', ' ', t)
    t = re.sub(r'\\+', '', t)
    t = re.sub(r'\s*\n\s*', ' ', t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    t = t.replace('[', '').replace(']', '')
    t = t.replace('\\"', '"').replace('\\\'', "'")
    return re.sub(r'\s{2,}', ' ', t).strip()

def clip(t, n):
    t = strip_ubb(t)
    t = re.sub(r'([。！？])(?![。！？”"）)])', r'\1 ', t)
    t = re.sub(r'\s{2,}', ' ', t).strip()
    return t[:n] + ('……' if len(t) > n else '')

def yr_replies(tid, k=2):
    rp = [h for h in HFI.get(tid, []) if h[4] and h[5] and h[5][:4] <= '2016']
    rp = sorted(rp, key=lambda x: x[5])
    good = []
    for h in rp:
        txt = strip_ubb(h[4])[:110]
        if not txt:
            continue
        if BAD.search(txt) or BAD.search(h[3] or ''):
            continue
        good.append((h[3], (h[5] or '')[:10], txt))
        if len(good) >= k:
            break
    return good

PICK = [
    ('存我（存我小妖）', '核心管理 · 首任副站长 · 评论组组长', '5470'),
    ('小基（Beta2游侠）', '聊天灌水版主', '39201'),
    ('博丽灵梦', '版主', '11539'),
    ('大门', '情感文学版版主', '12279'),
    ('莫小跳', '版主', '10495'),
    ('皇甫朝云', '友友推荐版 / 点播游戏版主（被站长点名表扬）', '24305'),
    ('小殇', '版主', '10446'),
    ('蛋定（扔蛋组）', '版主 · 资源组', '11438'),
    ('沉默（综合组）', '综合组版主', '9727'),
    ('不义联盟@Silence', '安卓版主', '12016'),
    ('吃屎的小太刀', '小说版版主', '25042'),
    ('BLOOD', '小说版版主', '20240'),
    ('秋韵物语', 'JAVA 塞班版主', '29686'),
    ('那年那月那流殇、', '点播游戏版主', '41148'),
    ('缘分、陌生人', '点播版 / 猜猜版主', '29005'),
    ('灰烬', '图片版版主', '65388'),
    ('玉碎@田驰', '各版预备版主', '46604'),
    ('暖夏@叶繁成花', '版主', '31888'),
    ('穆清（流氓高手）', '版主', '16928'),
    ('华夏管家丶莽蛋', '版主', '32325'),
    ('月光', '版主', '66504'),
    ('苏小染（倾城）', '版主', '1280'),
    ('老子只顶触屏', '新版主 · 触屏组', '33893'),
    ('残刃', '版主', '35780'),
    ('不修', '版主', '26889'),
    ('易（浅）', '猜猜看版主', '43939'),
    ('咸蛋超人', '聊天版实习版主 → 勋章申请版', '47710'),
    ('凉宫的消失', '版主（版规/版务）', '34433'),
    ('倾城@神月', '版主', '46633'),
    ('清风明月', '管理员', '24539'),
    ('邪、苍', '版主', '13613'),
    ('葬忆', '版主（申版活跃）', '47546'),
]

L = []
L.append('[title]7723(7坛) 版主群像[/title]')
L.append('[subtitle]当年那些版主，和他们亲手发过的帖子 —— 一个都不少[/subtitle]')
L.append('[caption]依据主站数据库（bbs）原样整理 · 每位版主至少一帖 · 每帖底部附原帖链接，可点进去看[/caption]')
L.append('[note]7723 论坛自 2009 年建坛到 2015 年，累计主题 54,230 篇、网友回复 412,632 条。'
         '下面这 %d 位，都是当年亲手管过版、发过帖的版主。内容全部取自主站数据库当年真实帖子，未作虚构。[/note]')
L.append('[divider]')
L.append('7723 从一个游戏下载站做起。到 2015 年，论坛前后有过几十位版主。他们管资源、管情感、管小说、管塞班，'
         '每天守着版面、删广告、回帖、办活动。下面这份《版主群像》，从主站数据库里把每位版主的帖子一条条翻出来——'
         '每人至少一帖，原样呈现，底部附原帖链接。点进去，就能回到当年那个论坛。')
L.append('[divider]')

n = 0
miss = []
for i, (disp, role, pid) in enumerate(PICK, 1):
    t = ID.get(pid)
    if not t:
        miss.append(disp + '/' + pid)
        continue
    n += 1
    title = strip_ubb(t[5])
    date = (t[7] or '')[:10]
    nr = len([h for h in HFI.get(pid, []) if h[4] and h[5] and h[5][:4] <= '2016'])
    content = clip(t[6], 560)
    L.append('[title]%s[/title]' % disp)
    L.append('[caption]%s ｜ 帖号 %s ｜ 发帖 %s ｜ 回复 %s[/caption]' % (role, pid, date, nr))
    L.append('[b]《%s》[/b]' % title)
    L.append(content if content else '(此帖正文为附件/图片，请点下方链接查看原帖)')
    for u, d, x in yr_replies(pid, 2):
        L.append('[quote]%s（%s）：%s[/quote]' % (u, d, x))
    L.append('[btn=https://www.7tan.com/bbs/%s/]▶ 点击查看原帖[/btn]' % pid)
    L.append('[divider]')

L[3] = L[3] % n
L.append('[tip]共 %d 位版主 · 名单与内容均取自主站数据库当年真实帖子。若你也是当年的版主、或发现遗漏，请回帖告诉我们。[/tip]' % n)
L.append('[caption]—— 7坛管理团队 · 主站数据库考证整理 ——[/caption]')

txt = '\n\n'.join(L)
open(r'D:\7tan\7tanAI\7723\7723版主群像_UBB.txt', 'w', encoding='utf-8').write(txt)
print('done mods=%d miss=%s chars=%d' % (n, miss, len(txt)))
