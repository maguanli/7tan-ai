import re, glob, os, json

# 静态解析：找 register_tool(...) 调用里的 name / description
pat_call = re.compile(r'register_tool\s*\(', re.S)

total_desc = 0
total_name = 0
total_params = 0
count = 0
per_plugin = []

for f in sorted(glob.glob(os.path.join('data', 'plugins', '*', 'tools.py'))):
    try:
        s = open(f, encoding='utf-8', errors='ignore').read()
    except Exception:
        continue
    # 粗粒度：抓所有 description= 后面的字符串字面量（支持三引号与单/双引号）
    ds = re.findall(r'description\s*=\s*("""(?:.|\n)*?"""|\'\'\'(?:.|\n)*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', s, re.S)
    ps = re.findall(r'parameters\s*=\s*\{', s)
    if not ds:
        per_plugin.append((os.path.basename(os.path.dirname(f)), 0, len(s), 0))
        continue
    chars = sum(len(d) for d in ds)
    total_desc += chars
    count += len(ds)
    per_plugin.append((os.path.basename(os.path.dirname(f)), len(ds), len(s), chars))

per_plugin.sort(key=lambda x: -x[3])
print('plugins        :', len(per_plugin))
print('description 数 :', count)
print('description 字符:', total_desc)
print('平均每条字符    :', round(total_desc / max(count, 1), 1))
print()
print('%-26s %6s %9s %8s' % ('plugin', 'tools', 'file_bytes', 'desc_chars'))
for name, n, sz, ch in per_plugin[:10]:
    print('%-26s %6d %9d %8d' % (name, n, sz, ch))
