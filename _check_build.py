data = open('build.bat', 'rb').read()
print('Size:', len(data))
print('Has chcp 65001:', b'chcp 65001' in data)
print('Has non-ASCII:', any(b > 127 for b in data))
