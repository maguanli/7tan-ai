lines = open("src/ui/chat_page.py", encoding="utf-8").readlines()
with open("data/_voice_gender_assign.txt", "w", encoding="utf-8") as out:
    for i, l in enumerate(lines, 1):
        if "_voice_gender" in l:
            out.write("L%d: %s\n" % (i, l.rstrip()[:200]))
print("Done")
