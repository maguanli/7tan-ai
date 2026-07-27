"""
为《当你被上司欺负后应该怎样做？》生成 7 张配图
使用 Pillow 程序化生成，每张 1200x800
"""
import os, math
from PIL import Image, ImageDraw, ImageFont

OUT = r"D:\7tan\7tanAI\article_images"
os.makedirs(OUT, exist_ok=True)

def find_font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for fp in candidates:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                continue
    return ImageFont.load_default()

def gradient_bg(draw, w, h, top, bot):
    for y in range(h):
        r = int(top[0] + (bot[0]-top[0])*y/h)
        g = int(top[1] + (bot[1]-top[1])*y/h)
        b = int(top[2] + (bot[2]-top[2])*y/h)
        draw.line([(0,y),(w,y)], fill=(r,g,b))

def draw_centered_text(draw, text, y, w, font, fill=(255,255,255)):
    bbox = draw.textbbox((0,0), text, font=font)
    tw = bbox[2]-bbox[0]
    draw.text(((w-tw)/2, y), text, fill=fill, font=font)

W, H = 1200, 800

# ============ 00_cover.png ============
img = Image.new('RGB', (W,H), (20,20,40))
draw = ImageDraw.Draw(img)
gradient_bg(draw, W, H, (30,30,60), (10,10,30))

# desk silhouette
for i in range(20):
    x = 400 + i*20
    y = 500 + int(30*math.sin(i*0.5))
    draw.line([(x,600),(x,y)], fill=(60,60,80), width=3)

# person at desk
draw.ellipse([560, 320, 640, 400], fill=(80,80,100))
draw.rectangle([580, 400, 620, 520], fill=(70,70,90))
draw.line([(590,520),(560,620)], fill=(70,70,90), width=8)
draw.line([(610,520),(640,620)], fill=(70,70,90), width=8)

# monitor glow
draw.ellipse([460, 280, 540, 440], fill=(20,40,80))

title_font = find_font(48, bold=True)
sub_font = find_font(28)
title = "当你被上司欺负后"
title2 = "应该怎样做？"
draw.text(((W-400)/2, 120), title, fill=(255,200,100), font=title_font)
draw.text(((W-300)/2, 180), title2, fill=(255,255,255), font=title_font)

draw.text((850, 650), "职场自救指南", fill=(180,180,200), font=sub_font)
img.save(os.path.join(OUT, "00_cover.png"))
print("00_cover.png OK")

# ============ 01_step1.png ============
img = Image.new('RGB', (W,H), (240,245,250))
draw = ImageDraw.Draw(img)
draw.rectangle([(0,0),(W,100)], fill=(41,128,185))
draw_centered_text(draw, "第一步：冷静分析", 20, W, find_font(38, True), (255,255,255))
draw_centered_text(draw, "这是欺负还是管理严格？", 60, W, find_font(22), (220,235,255))

# Left: normal
draw.rounded_rectangle([(60,130),(560,380)], radius=15, fill=(200,240,200), outline=(100,180,100), width=3)
draw_centered_text(draw, "正常管理", 145, 310, find_font(26, True), (30,120,30))
for i, item in enumerate(["方案被退回 - 批评指向具体工作", "标准统一 - 规则对所有人一样", "目的 - 把事情做好"]):
    draw.text((90, 200 + i*55), item, fill=(50,100,50), font=find_font(18))

# Right: bullying
draw.rounded_rectangle([(640,130),(1140,380)], radius=15, fill=(250,220,220), outline=(220,100,100), width=3)
draw_centered_text(draw, "职场霸凌", 145, 890, find_font(26, True), (180,30,30))
for i, item in enumerate(["当众羞辱 - 攻击人格尊严", "规则量身定制 - 只针对你", "目的 - 让你自我怀疑、主动离开"]):
    draw.text((670, 200 + i*55), item, fill=(150,40,40), font=find_font(18))

draw_centered_text(draw, "一旦确认是针对性的人际伤害，立刻停止从自己身上找原因。这不是你的错。", 430, W, find_font(20, True), (200,60,60))
# magnifying glass
draw.ellipse([300, 520, 400, 620], outline=(41,128,185), width=4)
draw.line([(390,610),(480,700)], fill=(41,128,185), width=6)
img.save(os.path.join(OUT, "01_step1.png"))
print("01_step1.png OK")

# ============ 02_step2.png ============
img = Image.new('RGB', (W,H), (25,25,45))
draw = ImageDraw.Draw(img)
gradient_bg(draw, W, H, (35,35,60), (20,20,40))
draw_centered_text(draw, "第二步：启动自我保护模式", 25, W, find_font(36, True), (255,200,100))

# Shield
cx, cy = 600, 420
draw.ellipse([cx-120,cy-140,cx+120,cy+100], fill=(60,60,100), outline=(120,120,180), width=4)

for i, (title, desc) in enumerate([
    ("心理抽离", "把自己当人类学家：数据点A - 上司又在贴标签，记录完毕"),
    ("工作留痕", "口头谈话后书面确认 / 定期汇报让凭空指责无处立足"),
    ("物理隔离", "减少独处 / 不舒服就找借口暂时离开"),
]):
    y = 530 + i*85
    draw.rounded_rectangle([(80, y-10), (1120, y+65)], radius=10, fill=(45,45,70), outline=(100,100,140), width=2)
    draw.text((110, y+5), title + " - " + desc, fill=(220,220,240), font=find_font(17))
img.save(os.path.join(OUT, "02_step2.png"))
print("02_step2.png OK")

# ============ 03_step3.png ============
img = Image.new('RGB', (W,H), (245,243,238))
draw = ImageDraw.Draw(img)
draw_centered_text(draw, "第三步：沉默、系统地收集证据", 25, W, find_font(36, True), (60,50,40))
draw_centered_text(draw, "这是你最硬的底牌。没有证据，一切控诉都是故事。", 70, W, find_font(20), (120,100,80))

for i, (icon, title, desc) in enumerate([
    ("(1)", "聊天截图", "微信/钉钉/邮件中含羞辱语言、不合理指派、功劳被夺"),
    ("(2)", "工作记录", "打卡、排班、加班 - 证明你正常履职"),
    ("(3)", "绩效文件", "业绩好但被打低分？留存数据+表扬信 - 矛盾证据链"),
    ("(4)", "录音", "公开场合多人谈话可录音，作整理文字证据的参考"),
    ("(5)", "证人", "与其他受害者低调沟通，确认是否愿意作证"),
]):
    y = 140 + i*120
    draw.rounded_rectangle([(80, y), (1120, y+100)], radius=12, fill=(255,255,255), outline=(180,170,160), width=2)
    draw.text((110, y+15), icon + " " + title, fill=(60,50,40), font=find_font(22, True))
    draw.text((110, y+55), desc, fill=(120,110,100), font=find_font(16))
draw_centered_text(draw, "保存到个人设备 + 云端，不要只存在公司电脑上！", 750, W, find_font(20, True), (200,50,50))
img.save(os.path.join(OUT, "03_step3.png"))
print("03_step3.png OK")

# ============ 04_step4.png ============
img = Image.new('RGB', (W,H), (250,248,245))
draw = ImageDraw.Draw(img)
draw_centered_text(draw, "第四步：选择合适的反击路径", 25, W, find_font(36, True), (50,40,30))
draw_centered_text(draw, "法律是你的武器", 70, W, find_font(22), (120,100,80))

for i, (title, desc, color) in enumerate([
    ("内部申诉", "向HR部门正式投诉\n向更高层管理者反映\n书面形式，附证据", (46,134,193)),
    ("劳动仲裁", "免费，不需要律师\n违法解除劳动合同\n恶意降薪降职等", (39,174,96)),
    ("民事诉讼", "名誉权侵害\n人格尊严侵害\n保留诊断证明", (243,156,18)),
    ("报警", "人身威胁、暴力\n非法拘禁\n110 或前往派出所", (192,57,43)),
]):
    x = 60 + i*280
    draw.rounded_rectangle([(x, 150), (x+250, 500)], radius=15, fill=(255,255,255), outline=color, width=3)
    draw_centered_text(draw, title, 180, x+125, find_font(24, True), color)
    lines = desc.split('\n')
    for j, line in enumerate(lines):
        draw_centered_text(draw, line, 250 + j*40, x+125, find_font(15), (80,70,60))
draw_centered_text(draw, "12333（人社服务热线）  |  12348（法律援助热线）", 560, W, find_font(24, True), (192,57,43))
draw_centered_text(draw, "注意：HR 的首要职责是保护公司，而非保护你。做好心理准备。", 620, W, find_font(18), (150,100,80))
img.save(os.path.join(OUT, "04_step4.png"))
print("04_step4.png OK")

# ============ 05_step5.png ============
img = Image.new('RGB', (W,H), (255,245,238))
draw = ImageDraw.Draw(img)
draw_centered_text(draw, "第五步：守护你的心灵", 25, W, find_font(38, True), (180,80,60))
draw_centered_text(draw, "身体是唯一罢工后无法重启的机器", 75, W, find_font(22), (160,120,100))

# heart
cx, cy = 600, 350
draw.ellipse([cx-50, cy-70, cx, cy-20], fill=(220,80,80))
draw.ellipse([cx, cy-70, cx+50, cy-20], fill=(220,80,80))
draw.polygon([(cx-50, cy-45), (cx+50, cy-45), (cx, cy+50)], fill=(220,80,80))

for i, (title, desc) in enumerate([
    ("看心理咨询师", "跟感冒看医生一样正常，不需要为此感到羞耻"),
    ("进入心流状态", "拼图、烘焙、运动 - 把注意力从反刍痛苦中拉出来"),
    ("找回价值感", "列出你的十个优点，让朋友帮你确认"),
]):
    y = 510 + i*90
    draw.rounded_rectangle([(120, y), (1080, y+75)], radius=12, fill=(255,255,255), outline=(220,180,160), width=2)
    draw.text((150, y+10), title, fill=(180,80,60), font=find_font(22, True))
    draw.text((150, y+42), desc, fill=(120,100,90), font=find_font(17))
draw_centered_text(draw, "你的价值，从来不取决于那个伤害你的人的评价。", 770, W, find_font(20, True), (180,80,60))
img.save(os.path.join(OUT, "05_step5.png"))
print("05_step5.png OK")

# ============ 06_exit.png ============
img = Image.new('RGB', (W,H), (20,30,45))
draw = ImageDraw.Draw(img)
gradient_bg(draw, W, H, (30,40,60), (15,20,35))
draw_centered_text(draw, "何时必须离开？", 40, W, find_font(40, True), (255,180,80))
draw_centered_text(draw, "离开不是失败，是及时止损", 95, W, find_font(24), (200,200,220))

# Door with light
draw.rectangle([(450, 220), (750, 650)], fill=(60,50,40), outline=(100,90,80), width=3)
for i in range(30):
    alpha = max(255 - i*8, 0)
    draw.ellipse([450-i*10, 300-i*10, 750+i*10, 650+i*10], fill=(255,220,150))

for i, (icon, desc) in enumerate([
    ("(1)", "霸凌已严重损害身心健康，诊断证明在提醒你临界点"),
    ("(2)", "内部申诉后，公司明显包庇甚至默许报复"),
    ("(3)", "公司文化就是弱肉强食，你确认是在消耗生命"),
]):
    y = 130 + i*80
    draw.text((100, y), icon + " " + desc, fill=(220,200,180), font=find_font(19))

draw_centered_text(draw, "把自己从这个有毒的环境中连根拔起", 680, W, find_font(22, True), (255,200,120))
draw_centered_text(draw, "重新种在一片能让你生长的土壤里", 710, W, find_font(22, True), (255,255,255))
draw_centered_text(draw, "这不叫放弃，这叫自救。", 750, W, find_font(24, True), (255,180,80))
img.save(os.path.join(OUT, "06_exit.png"))
print("06_exit.png OK")

print("\n=== ALL DONE ===")
print(f"Output: {OUT}")
for f in sorted(os.listdir(OUT)):
    print(f"  {f}")
