# -*- coding: utf-8 -*-
import base64

# owner.dat 内容（从审计中读取）
raw = "fSJuYVQ3IiA6InBwYSIgLCJiYTc1YTZiMjY5MzI3MzRmZWIwM2FlOGJjMjg5YmY2NSIgOiJwZiIgLDUwMDA5NjU4NzEgOiJzdCIgLCJpbGEiIDoicmVzdSJ7"

# 先反转（文件是倒序存储）
rev = raw[::-1]
print("反转后:", rev)
try:
    dec = base64.b64decode(rev).decode('utf-8', errors='replace')
    print("解密内容:", dec)
except Exception as e:
    print("base64 解码失败:", e)
    # 尝试补 padding
    try:
        dec = base64.b64decode(rev + "==").decode('utf-8', errors='replace')
        print("补 padding 后:", dec)
    except Exception as e2:
        print("仍失败:", e2)

# 检查 sec_config.pyd 内置公钥
fp = r'D:\7tan\7tanAI\dist\7tan-editor\_internal\src\security\sec_config.pyd'
data = open(fp, 'rb').read()
import re
# 找 PEM 公钥
pem = re.findall(rb'-----BEGIN PUBLIC KEY-----.*?-----END PUBLIC KEY-----', data, re.S)
print(f"\nsec_config.pyd 内嵌 PEM 公钥: {len(pem)} 个")
for p in pem[:2]:
    print("  ", p[:80])
# 找 pin 表相关（7tan.com / 7tan.cn 域名）
for d in [b'www.7tan.com', b'img.7tan.cn', b'7tan.com']:
    print(f"  含 {d.decode()}: {data.count(d)} 处")

# auth_client.pyd 是否含 update 相关端点/域名
fp2 = r'D:\7tan\7tanAI\dist\7tan-editor\_internal\src\security\auth_client.pyd'
d2 = open(fp2, 'rb').read()
for pat in [b'7tan.com', b'login.php', b'verify.php', b'device.php', b'X-Device-Id']:
    print(f"  auth_client 含 {pat.decode(errors='ignore')}: {d2.count(pat)} 处")
