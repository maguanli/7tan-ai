# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

p = r'D:\7tan\7tan_cn_20260515_090725.sql'
with open(p, 'r', encoding='utf-16', errors='ignore') as f:
    data = f.read()

def rows_of(table):
    """返回该表所有 INSERT 的原始值串列表（未拆列）"""
    out = []
    for m in re.finditer(r"INSERT INTO `"+re.escape(table)+r"` \([^)]*\) VALUES (.*?);\n", data, re.S):
        out.append(m.group(1))
    return out

def split_top(s):
    """按顶层逗号切分一行元组里的字段，尊重引号与转义"""
    vals=[]; cur=''; i=0; n=len(s); depth=0; q=False
    while i<n:
        c=s[i]
        if q:
            if c=='\\':
                cur+=c+s[i+1] if i+1<n else c; i+=2; continue
            if c=="'":
                if i+1<n and s[i+1]=="'":
                    cur+="''"; i+=2; continue
                q=False; cur+=c; i+=1; continue
            cur+=c; i+=1; continue
        else:
            if c=="'":
                q=True; cur+=c; i+=1; continue
            if c=='(':
                depth+=1; cur+=c; i+=1; continue
            if c==')':
                depth-=1; cur+=c; i+=1; continue
            if c==',' and depth==0:
                vals.append(cur); cur=''; i+=1; continue
            cur+=c; i+=1; continue
    if cur: vals.append(cur)
    return vals

# 版块
print('=== 版块 ll_lt_bankuai ===')
for blob in rows_of('ll_lt_bankuai'):
    # 拆 (..),(..)
    for row in re.findall(r'\((.*?)\)(?:,\(|$)', blob, re.S):
        v=split_top(row)
        print(v)

# 子论坛 ll_ltzt
print('\n=== ll_ltzt ===')
for blob in rows_of('ll_ltzt'):
    for row in re.findall(r'\((.*?)\)(?:,\(|$)', blob, re.S):
        v=split_top(row)
        print(v)
