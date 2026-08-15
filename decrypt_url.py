# -*- coding: utf-8 -*-
import base64, urllib.parse, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

data = 'SzI3VBVGVCl7F2J7FyBLIy9USAQGBTMLXipCB04jbUcJDkJaGFVWN1MHQD9uSA8EDxxwTVAzSQ=='
key = '#FC$fcgh^%$^%f'

binary = base64.b64decode(data)
key_bytes = key.encode('utf-8')
result = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(binary))
url = urllib.parse.unquote(result.decode('utf-8'))
print('REAL URL:', url)
