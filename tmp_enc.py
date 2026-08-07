import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

path = r'D:\7tan\7tanAI\build_and_sync.bat'
raw = open(path, 'rb').read()
print('SIZE:', len(raw))
print('HEAD_BYTES:', raw[:40])
print('HAS_UTF8_BOM:', raw[:3] == b'\xef\xbb\xbf')

# 尝试解码
for enc in ['utf-8', 'gbk']:
    try:
        txt = raw.decode(enc)
        print(f'DECODE_OK: {enc}')
    except Exception as e:
        print(f'DECODE_FAIL: {enc} -> {e}')

# 找到新增段落位置
try:
    txt = raw.decode('utf-8')
    idx = txt.find('Step 0.75')
    print('FOUND_0.75_AT:', idx)
except Exception:
    try:
        txt = raw.decode('gbk')
        idx = txt.find('Step 0.75')
        print('FOUND_0.75_AT(gbk):', idx)
    except Exception as e:
        print('both fail', e)
