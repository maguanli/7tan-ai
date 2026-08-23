from PIL import Image
base = r"D:\7tan\7tanAI\镜像同事_小说\定妆图"
a = Image.open(base + r"\character_jiangchen_main_comic.png").convert("RGB")
b = Image.open(base + r"\_verify_image_array.png").convert("RGB")
h = max(a.height, b.height)
a = a.resize((int(a.width*h/a.height), h))
b = b.resize((int(b.width*h/b.height), h))
c = Image.new("RGB", (a.width+b.width+12, h), (255,255,255))
c.paste(a, (0,0))
c.paste(b, (a.width+12, 0))
c.save(base + r"\_cmp_verify.png")
print("ok, size=", c.size)
