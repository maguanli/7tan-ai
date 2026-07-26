"""
为《人性，你知道多少？》生成 8 张配图
使用 Pillow 程序化生成，每张 1200x800
"""
import os, math, random
from PIL import Image, ImageDraw, ImageFont

OUT = r"D:\7tan\7tanAI\output\human_nature"

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

def center_text(draw, text, y, font, color, w=1200):
    bbox = draw.textbbox((0,0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((w-tw)//2, y), text, font=font, fill=color)

def save(img, name):
    fp = os.path.join(OUT, name)
    img.save(fp, quality=92)
    print(f"  [OK] {name}")

# ═══════════════ 图1: 封面 ═══════════════
def make_cover():
    w, h = 1200, 800
    img = Image.new("RGB", (w,h), (0,0,0))
    draw = ImageDraw.Draw(img)
    gradient_bg(draw, w, h, (10,10,30), (30,15,50))
    cx, cy = w//2, h//2
    draw.ellipse([cx-180,cy-180,cx+180,cy+180], fill=(20,25,50))
    draw.pieslice([cx-180,cy-180,cx+180,cy+180], -90, 90, fill=(50,20,30))
    for i in range(5):
        rr = 182 + i*2
        draw.ellipse([cx-rr,cy-rr,cx+rr,cy+rr], outline=(100+i*20,100+i*20,140+i*15), width=2)
    random.seed(42)
    for _ in range(50):
        angle = random.uniform(math.pi/2, 3*math.pi/2)
        dist = random.uniform(20,170)
        px = int(cx + math.cos(angle)*dist)
        py = int(cy + math.sin(angle)*dist)
        sz = random.randint(1,3)
        draw.ellipse([px-sz,py-sz,px+sz,py+sz], fill=(200,220,255))
    center_text(draw, "人性，你知道多少？", 200, find_font(52,True), (255,255,255))
    center_text(draw, "—— 一场关于善恶、深渊与星空的对话", 275, find_font(22), (180,180,210))
    center_text(draw, "7Tan · 深度人文系列", 720, find_font(16), (140,140,160))
    save(img, "01_封面.png")

# ═══════════════ 图2: 善vs恶 ═══════════════
def make_good_vs_evil():
    w, h = 1200, 800
    img = Image.new("RGB", (w,h), (245,245,250))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        r = int(255 - 20*y/h)
        g = int(250 - 15*y/h)
        b = int(235 - 10*y/h)
        draw.line([(0,y),(w//2,y)], fill=(r,g,b))
        r2 = int(50 + 50*y/h)
        g2 = int(40 + 40*y/h)
        b2 = int(60 + 60*y/h)
        draw.line([(w//2,y),(w,y)], fill=(r2,g2,b2))
    draw.line([(w//2,0),(w//2,h)], fill=(180,180,180), width=3)
    cx, cy = w//2, h//2
    draw.ellipse([cx-60,cy-60,cx+60,cy+60], fill=(255,255,255), outline=(180,180,180), width=2)
    draw.pieslice([cx-60,cy-60,cx+60,cy+60], -90, 90, fill=(40,40,50))
    draw.ellipse([cx-14,cy-38,cx+14,cy-10], fill=(40,40,50))
    draw.ellipse([cx-14,cy+10,cx+14,cy+38], fill=(255,255,255))
    f1 = find_font(40,True); f2 = find_font(24); f3 = find_font(18)
    draw.text((120,200), "孟子", font=f1, fill=(80,50,10))
    draw.text((120,260), "「人之初，性本善」", font=f2, fill=(120,80,20))
    draw.text((120,320), "恻隐之心，人皆有之\n羞恶之心，人皆有之\n辞让之心，人皆有之\n是非之心，人皆有之", font=f3, fill=(100,70,30))
    draw.text((750,200), "荀子", font=f1, fill=(220,200,200))
    draw.text((750,260), "「人之性恶，其善者伪也」", font=f2, fill=(200,170,150))
    draw.text((750,320), "生而好利，故争夺生\n生而疾恶，故残贼生\n生而有欲，故淫乱生\n善者，后天教化之伪", font=f3, fill=(180,150,130))
    center_text(draw, "那个古老的问题：性本善，还是性本恶？", 650, find_font(28,True), (60,60,80))
    center_text(draw, "？", 690, find_font(72,True), (150,80,80))
    save(img, "02_善vs恶.png")

# ═══════════════ 图3: 实验 ═══════════════
def make_experiments():
    w, h = 1200, 800
    img = Image.new("RGB", (w,h), (25,25,35))
    draw = ImageDraw.Draw(img)
    center_text(draw, "那些让人沉默的实验", 40, find_font(36,True), (255,255,255))
    center_text(draw, "当普通人被置于特定环境中，良知与恶行的边界变得模糊", 95, find_font(20), (160,160,180))
    panels = [
        ("01", "斯坦福监狱实验", "1971 · 津巴多",
         "普通大学生随机扮演\n「狱警」与「囚犯」\n仅6天就被迫终止\n环境轻易吞噬了良知",
         (180,100,60), 50),
        ("02", "米尔格拉姆服从实验", "1961 · 米尔格拉姆",
         "权威人物要求施加电击\n65%的人加到致命450伏\n服从权威，比想象中\n更容易",
         (60,130,180), 430),
        ("03", "旁观者效应", "1964 · 纽约凶杀案",
         "女子被刺身亡\n38位邻居目睹全程\n却无一人报警\n责任被稀释，善意蒸发",
         (140,100,180), 810),
    ]
    fn = find_font(60,True); ft = find_font(22,True); fy = find_font(14); fb = find_font(16)
    for num, title, year, desc, color, px in panels:
        draw.rounded_rectangle([px,160,px+330,650], radius=16, fill=(38,38,52), outline=color, width=2)
        draw.text((px+20,180), num, font=fn, fill=color)
        draw.text((px+20,260), title, font=ft, fill=(255,255,255))
        draw.text((px+20,300), year, font=fy, fill=(150,150,160))
        draw.line([(px+20,340),(px+310,340)], fill=color, width=1)
        draw.text((px+20,360), desc, font=fb, fill=(200,200,210), spacing=6)
    center_text(draw, "它们揭示的不是「人性本恶」，而是：在特定环境下，普通人可以做出令人震惊的事情", 730, find_font(18), (200,200,220))
    save(img, "03_实验.png")

# ═══════════════ 图4: 暗面 ═══════════════
def make_dark_side():
    w, h = 1200, 800
    img = Image.new("RGB", (w,h), (15,13,20))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        rr = int(15 + 30*math.sin(y/h*math.pi*0.7))
        draw.line([(0,y),(w,y)], fill=(rr,13,20+int(15*y/h)))
    center_text(draw, "人性的暗面", 60, find_font(42,True), (240,200,180))
    center_text(draw, "每个人身上都有一些不愿直视的角落", 120, find_font(20), (180,150,140))
    cards = [
        ("自私的基因", "帮助他人之前，大脑的\n「计算中心」已在评估成本\n和收益。利他行为，\n某种程度上也是基因的自私。", (255,140,80)),
        ("内群体偏爱", "本能地偏袒「自己人」，\n排斥「外人」。种族歧视、\n地域偏见，根源在这里。", (255,100,120)),
        ("认知偏差", "确认偏误让我们只看到\n支持自己的证据。\n达克效应让最无知的\n人最自信。", (180,130,255)),
        ("道德许可", "做了一件好事之后，\n反而更容易放纵自己——\n「今天健身了，\n所以可以吃个蛋糕。」", (120,200,160)),
    ]
    positions = [(80,200),(630,200),(80,500),(630,500)]
    fw = find_font(22,True); fd = find_font(15)
    for (title, desc, color), (cx,cy) in zip(cards, positions):
        draw.rounded_rectangle([cx,cy,cx+500,cy+260], radius=14, fill=(30,28,38), outline=color, width=1)
        draw.text((cx+28,cy+22), title, font=fw, fill=color)
        draw.line([(cx+28,cy+60),(cx+180,cy+60)], fill=color, width=2)
        draw.text((cx+28,cy+80), desc, font=fd, fill=(200,195,190), spacing=5)
    center_text(draw, "承认这些，不是为恶行开脱。只有直面黑暗，才能真正理解光明。", 750, find_font(17), (200,180,160))
    save(img, "04_暗面.png")

# ═══════════════ 图5: 光明 ═══════════════
def make_light_side():
    w, h = 1200, 800
    img = Image.new("RGB", (w,h), (255,248,235))
    draw = ImageDraw.Draw(img)
    gradient_bg(draw, w, h, (255,240,220), (255,252,245))
    center_text(draw, "人性也有令人热泪盈眶的时刻", 50, find_font(38,True), (120,50,20))
    center_text(draw, "同理心、自我牺牲、利他精神——这些也是人性，真实而有力", 108, find_font(18), (160,100,60))
    scenes = [
        ("汶川地震 · 2008",
         "「亲爱的宝贝，如果你能活着，\n记住妈妈爱你。」",
         "母亲用身体护住婴儿，\n手机屏幕上是最后的告白。",
         60, (255,235,215)),
        ("武汉 · 2020",
         "「党员先上！」",
         "医护人员头也不回地\n走进重症病房，\n防护服上的字是最好的誓言。",
         430, (235,245,255)),
        ("无名之人",
         "「他们比我更需要。」",
         "流浪汉把仅有的20块钱\n塞进捐款箱。\n善良从不需要理由。",
         800, (240,255,240)),
    ]
    for title, quote, desc, x, bg in scenes:
        draw.rounded_rectangle([x,180,x+320,620], radius=18, fill=bg, outline=(200,180,160), width=1)
        draw.text((x+28,210), title, font=find_font(20,True), fill=(80,40,20))
        draw.text((x+28,260), quote, font=find_font(16), fill=(180,80,40), spacing=4)
        draw.line([(x+28,330),(x+280,330)], fill=(200,150,100), width=1)
        draw.text((x+28,350), desc, font=find_font(15), fill=(100,70,50), spacing=4)
    center_text(draw, "神经科学发现：当人们做出善举时，大脑的奖赏中枢会亮起——善良本身就是一种奖赏。", 700, find_font(18), (130,90,40))
    center_text(draw, "✦  善良，是刻在人类基因里的光芒  ✦", 745, find_font(20,True), (180,100,30))
    save(img, "05_光明.png")

# ═══════════════ 图6: 如水 ═══════════════
def make_water():
    w, h = 1200, 800
    img = Image.new("RGB", (w,h), (240,245,255))
    draw = ImageDraw.Draw(img)
    gradient_bg(draw, w, h, (230,240,255), (200,225,250))
    center_text(draw, "人性不是固定的，它是流动的", 50, find_font(40,True), (30,60,120))
    center_text(draw, "人性像水。装进圆杯就是圆的，装进方杯就是方的。", 115, find_font(20), (80,100,150))
    shapes = [
        ("circle", 200, "善的制度", "激发善良"),
        ("square", 480, "恶的环境", "诱发恶行"),
        ("triangle", 760, "文化熏陶", "塑造品格"),
        ("hexagon", 1040, "教育引导", "开启心智"),
    ]
    for shape, sx, label, sub in shapes:
        cx, cy = sx, 340
        if shape == "circle":
            draw.ellipse([cx-80,cy-20,cx+80,cy+150], outline=(100,130,180), width=4)
            draw.ellipse([cx-76,cy+10,cx+76,cy+146], fill=(100,160,220))
            draw.ellipse([cx-60,cy+10,cx+60,cy+30], outline=(140,190,240), width=2)
        elif shape == "square":
            draw.rectangle([cx-75,cy-15,cx+75,cy+140], outline=(100,130,180), width=4)
            draw.rectangle([cx-71,cy+15,cx+71,cy+136], fill=(100,160,220))
            draw.rectangle([cx-55,cy+15,cx+55,cy+33], outline=(140,190,240), width=2)
        elif shape == "triangle":
            pts = [(cx,cy-30),(cx-85,cy+140),(cx+85,cy+140)]
            draw.polygon(pts, outline=(100,130,180), width=4)
            wpts = [(cx,cy+20),(cx-70,cy+136),(cx+70,cy+136)]
            draw.polygon(wpts, fill=(100,160,220))
        elif shape == "hexagon":
            r = 85
            pts = [(cx+r*math.cos(math.pi/6+i*math.pi/3), cy+55+r*math.sin(math.pi/6+i*math.pi/3)) for i in range(6)]
            draw.polygon(pts, outline=(100,130,180), width=4)
            wpts = [(cx-73,cy+55),(cx-42,cy+128),(cx+42,cy+128),(cx+73,cy+55)]
            draw.polygon(wpts, fill=(100,160,220))
        fl = find_font(18,True); fs = find_font(15)
        bbox = draw.textbbox((0,0), label, font=fl)
        draw.text((sx-(bbox[2]-bbox[0])//2, 490), label, font=fl, fill=(30,60,120))
        bbox2 = draw.textbbox((0,0), sub, font=fs)
        draw.text((sx-(bbox2[2]-bbox2[0])//2, 520), sub, font=fs, fill=(100,130,170))
    center_text(draw, "「好的制度让坏人做不了坏事，坏的制度让好人做不了好事。」", 630, find_font(22,True), (40,70,130))
    center_text(draw, "与其问人性是善是恶，不如问：我们在创造一个什么样的环境，来激发人性的哪一面？", 680, find_font(18), (80,110,160))
    save(img, "06_如水.png")

# ═══════════════ 图7: 理解自己 ═══════════════
def make_understand_self():
    w, h = 1200, 800
    img = Image.new("RGB", (w,h), (248,245,250))
    draw = ImageDraw.Draw(img)
    gradient_bg(draw, w, h, (248,245,250), (230,225,240))
    center_text(draw, "理解人性，最终是为了理解自己", 45, find_font(42,True), (60,40,80))
    center_text(draw, "了解人性，不是为了变得愤世嫉俗，而是为了——", 110, find_font(20), (120,100,130))
    steps = [
        ("1", "对自己诚实", "承认自己有阴暗面，不意味着\n屈服于它。自我觉察是改变\n的第一步。", (200,130,80)),
        ("2", "对他人宽容", "理解每个人都在和自己的恶魔\n搏斗，少一些评判，\n多一些理解。", (80,150,100)),
        ("3", "设计更好的世界", "用制度引导人性向善，\n而不是指望每个人\n都是圣人。", (80,110,200)),
    ]
    for i, (num, title, desc, color) in enumerate(steps):
        y = 200 + i*190
        draw.ellipse([80,y+10,155,y+85], fill=color)
        draw.text((105,y+25), num, font=find_font(48,True), fill=(255,255,255))
        draw.text((200,y+15), title, font=find_font(28,True), fill=color)
        draw.text((200,y+60), desc, font=find_font(17), fill=(80,70,90), spacing=4)
        if i < 2:
            draw.line([(117,y+85),(117,y+190)], fill=(200,200,210), width=2)
    # mirror
    mcx, mcy = 920, 430
    draw.ellipse([mcx-120,mcy-140,mcx+120,mcy+140], fill=(220,215,230), outline=(160,150,170), width=4)
    draw.ellipse([mcx-80,mcy-100,mcx+80,mcy+100], fill=(235,230,245))
    draw.ellipse([mcx-35,mcy-60,mcx+35,mcy+10], fill=(200,195,210))
    draw.ellipse([mcx-10,mcy-45,mcx-3,mcy-38], fill=(120,110,140))
    draw.ellipse([mcx+3,mcy-45,mcx+10,mcy-38], fill=(120,110,140))
    draw.arc([mcx-12,mcy-30,mcx+12,mcy-15], 0, 180, fill=(120,110,140), width=2)
    center_text(draw, "了解人性，最终是一场与自己的和解。", 740, find_font(20,True), (80,60,100))
    save(img, "07_理解自己.png")

# ═══════════════ 图8: 镜子 ═══════════════
def make_mirror():
    w, h = 1200, 800
    img = Image.new("RGB", (w,h), (5,5,12))
    draw = ImageDraw.Draw(img)
    gradient_bg(draw, w, h, (5,5,18), (15,10,35))
    random.seed(7)
    for _ in range(200):
        sx = random.randint(0,w); sy = random.randint(0,h)
        ss = random.randint(1,3); br = random.randint(120,255)
        draw.ellipse([sx-ss,sy-ss,sx+ss,sy+ss], fill=(br,br,br))
    cx, cy = w//2, h//2; r = 200
    draw.pieslice([cx-r,cy-r,cx+r,cy+r], 90, 270, fill=(15,20,60))
    draw.pieslice([cx-r,cy-r,cx+r,cy+r], -90, 90, fill=(50,15,20))
    random.seed(77)
    for _ in range(60):
        angle = random.uniform(math.pi/2, 3*math.pi/2)
        dist = random.uniform(15,190)
        px = int(cx+math.cos(angle)*dist); py = int(cy+math.sin(angle)*dist)
        sz = random.randint(1,3)
        draw.ellipse([px-sz,py-sz,px+sz,py+sz], fill=(200,210,255))
    for _ in range(20):
        angle = random.uniform(-math.pi/2, math.pi/2)
        dist = random.uniform(20,185)
        px = int(cx+math.cos(angle)*dist); py = int(cy+math.sin(angle)*dist)
        draw.ellipse([px-3,py-3,px+3,py+3], fill=(80,30,35))
    for i in range(6):
        rr = r+3+i*3
        draw.ellipse([cx-rr,cy-rr,cx+rr,cy+rr], outline=(100+i*15,100+i*15,120+i*15), width=1)
    center_text(draw, "人性是一面镜子", 60, find_font(46,True), (230,230,250))
    center_text(draw, "照见的既是深渊，也是星空", 125, find_font(24), (180,180,200))
    center_text(draw, "知道黑暗存在，依然选择走向光明 —— 这，或许就是人性中最美的那部分。", 680, find_font(22,True), (220,200,180))
    center_text(draw, "那么，你呢？你对人性，知道多少？", 730, find_font(20), (200,180,150))
    center_text(draw, "—— 7Tan · 深度人文系列 ——", 770, find_font(15), (120,110,140))
    save(img, "08_镜子.png")

# ═══════════════ MAIN ═══════════════
if __name__ == "__main__":
    print("Generating images for 《人性，你知道多少？》...\n")
    make_cover()
    make_good_vs_evil()
    make_experiments()
    make_dark_side()
    make_light_side()
    make_water()
    make_understand_self()
    make_mirror()
    print(f"\nAll done! Saved to: {OUT}")
