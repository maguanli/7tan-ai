lines = open("src/ui/chat_page.py", encoding="utf-8").readlines()
for i, l in enumerate(lines, 1):
    if "_voice_btn" in l:
        print("L%d: %s" % (i, l.rstrip()[:200]))
