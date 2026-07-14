import sys

with open(r"c:\Users\Administrator\7tan-auto-updater\ARCHITECTURE.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

depth = 0
markers = []
issues = []

for i, line in enumerate(lines, 1):
    if line.rstrip() == "```":
        markers.append(i)
        if depth > 0:
            depth -= 1
        else:
            depth += 1

print(f"Code block markers found: {len(markers)}")
print(f"Final depth: {depth}")
print(f"PASS: All blocks balanced" if depth == 0 else f"FAIL: {depth} unclosed blocks")
print(f"Markers at lines: {markers}")
