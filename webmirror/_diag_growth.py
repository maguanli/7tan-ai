import json, os, collections, re, glob

D = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'

def lines(p):
    if not os.path.exists(p):
        return -1
    n = 0
    with open(p, 'rb') as f:
        for _ in f:
            n += 1
    return n

q = os.path.join(D, '_mirror_queue.ndjson')
m = os.path.join(D, '_mirror_manifest.ndjson')
s = os.path.join(D, '_mirror_state.json')

print('queue_lines   ', lines(q))
print('manifest_lines', lines(m))
print('state_size_MB ', round(os.path.getsize(s)/1048576, 1) if os.path.exists(s) else -1)
print('queue_size_MB ', round(os.path.getsize(q)/1048576, 1) if os.path.exists(q) else -1)

# sample queue lines
print('--- queue sample ---')
with open(q, encoding='utf-8') as f:
    for i, l in enumerate(f):
        if i < 3:
            print(repr(l[:200]))
        else:
            break

# read state json keys
print('--- state keys ---')
with open(s, encoding='utf-8') as f:
    st = json.load(f)
print(type(st), list(st.keys())[:10] if isinstance(st, dict) else len(st))
if isinstance(st, dict):
    for k, v in st.items():
        try:
            print(' ', k, type(v).__name__, len(v) if hasattr(v, '__len__') else v)
        except Exception as e:
            print(' ', k, 'ERR', e)

# analyze queue urls
print('--- queue url analysis ---')
urls = []
pat = re.compile(r'"url"\s*:\s*"([^"]+)"')
with open(q, encoding='utf-8') as f:
    for l in f:
        mt = pat.search(l)
        if mt:
            urls.append(mt.group(1))
print('parsed', len(urls))
print('unique exact', len(set(urls)))
low = [u.lower() for u in urls]
print('unique lower', len(set(low)))

# shape analysis: strip id_ prefix and .html
def shape(u):
    p = u.split('youbian.293.net', 1)[-1]
    p = re.sub(r'id_[A-Za-z0-9]+', 'id_XXX', p)
    p = re.sub(r'\d+', 'N', p)
    return p
sh = collections.Counter(shape(u) for u in urls)
print('--- top url shapes ---')
for k, v in sh.most_common(15):
    print('  ', v, k)

# count by prefix of id
pref = collections.Counter()
for u in urls:
    mt = re.search(r'id_([A-Za-z0-9]{2})', u)
    if mt:
        pref[mt.group(1)] += 1
print('--- id prefix (first 2 chars) top ---')
for k, v in pref.most_common(15):
    print('  ', v, k)

# domain / path variety
ext = collections.Counter(os.path.splitext(u.split('?')[0])[1] for u in urls)
print('--- ext ---', ext.most_common(10))
print('with query', sum(1 for u in urls if '?' in u))
print('sample urls:', urls[:5])
