lines = open("src/ui/chat_page.py", encoding="utf-8").readlines()
with open("data/_voice_check_result.txt", "w", encoding="utf-8") as out:
    for i, l in enumerate(lines, 1):
        if "_voice_btn" in l:
            out.write("L%d: %s\n" % (i, l.rstrip()[:200]))
print("Done, check data/_voice_check_result.txt")
