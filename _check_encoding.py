import os

path = r"D:\7tan\7tanAI\build.bat"
with open(path, 'rb') as f:
    data = f.read()

print(f"File size: {len(data)} bytes")
print(f"First 3 bytes (BOM check): {data[:3].hex()}")

# Check if it's valid UTF-8
try:
    text = data.decode('utf-8')
    print("Valid UTF-8: YES")
except UnicodeDecodeError as e:
    print(f"Invalid UTF-8 at byte {e.start}: {e}")

# Check for CRLF vs LF
crlf_count = data.count(b'\r\n')
lf_only = data.count(b'\n') - crlf_count
print(f"CRLF: {crlf_count}, LF-only: {lf_only}")

# Show lines around line 55-70
lines = data.split(b'\n')
for i in range(54, min(75, len(lines))):
    line = lines[i]
    try:
        decoded = line.decode('utf-8')
        print(f"Line {i+1}: {decoded[:150]}")
    except:
        print(f"Line {i+1}: [binary] {line[:60].hex()}")

# Also show all lines that contain non-ASCII
print("\n--- Lines with non-ASCII chars ---")
for i, line in enumerate(lines):
    try:
        decoded = line.decode('utf-8')
        if any(ord(c) > 127 for c in decoded):
            print(f"Line {i+1}: {decoded[:150]}")
    except:
        print(f"Line {i+1}: [BINARY] {line[:80].hex()}")
