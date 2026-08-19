# -*- coding: utf-8 -*-
import ast, sys
p = r"D:\7tan\7tanAI\scripts\sendinput_text.py"
src = open(p, encoding="utf-8").read()
ast.parse(src)
print("SYNTAX_OK")
