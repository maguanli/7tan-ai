# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

p = r'D:\7tan\7tan_cn_20260515_090725.sql'
with open(p, 'r', encoding='utf-16', errors='ignore') as f:
    data = f.read()

def unescape_mysql(s):
    if s=="NULL": return None
    if len(s)>=2 and s[0]=="'" and s[-1]=="'":
        s=s[1:-1]
    # mysql escapes
    out=[]; i=0
    while i<len(s):
        c=s[i]
        if c=='\\' and i+1<len(s):
            nx=s[i+1]
            mp={'n':'\n','r':'\r','t':'\t','0':'\0','\\':'\\',"'":"'",'"':'"','Z':'\x1a','b':'\b'}
            out.append(mp.get(nx,nx)); i+=2
        else:
            out.append(c); i+=1
    return ''.join(out)

def parse_rows(table):
    """返回 list of list of raw value-string (已去引号/反转义 为最后一步)"""
    rows=[]
    for m in re.finditer(r"INSERT INTO `"+re.escape(table)+r"` VALUES (.*?);\n", data, re.S):
        blob=m.group(1)
        # 遍历顶层元组
        i=0; n=len(blob)
        while i<n:
            if blob[i]!='(': i+=1; continue
            # read until matching ')'
            depth=0; q=False; j=i; cur=''
            while j<n:
                c=blob[j]
                if q:
                    if c=='\\': cur+=c+blob[j+1] if j+1<n else c; j+=2; continue
                    if c=="'":
                        if j+1<n and blob[j+1]=="'": cur+="''"; j+=2; continue
                        q=False; cur+=c; j+=1; continue
                    cur+=c; j+=1; continue
                else:
                    if c=="'": q=True; cur+=c; j+=1; continue
                    if c=='(':
                        depth+=1; cur+=c if depth>1 else ''; j+=1; continue
                    if c==')':
                        depth-=1
                        if depth==0:
                            j+=1; break
                        cur+=c; j+=1; continue
                    if c==',':
                        # split
                        pass
                    cur+=c; j+=1; continue
            # cur 是元组内部字符串
            rows.append(split_fields(cur))
            i=j
    return rows

def split_fields(s):
    vals=[]; cur=''; i=0; n=len(s); q=False
    while i<n:
        c=s[i]
        if q:
            if c=='\\': cur+=c+(s[i+1] if i+1<n else ''); i+=2; continue
            if c=="'":
                if i+1<n and s[i+1]=="'": cur+="''"; i+=2; continue
                q=False; cur+=c; i+=1; continue
            cur+=c; i+=1; continue
        else:
            if c=="'": q=True; cur+=c; i+=1; continue
            if c==',':
                vals.append(cur); cur=''; i+=1; continue
            cur+=c; i+=1; continue
    vals.append(cur)
    return vals

# 测试
for t in ['ll_lt_bankuai','ll_ltzt']:
    r=parse_rows(t)
    print(f'=== {t}: {len(r)} rows ===')
    for row in r[:40]:
        print([unescape_mysql(x) for x in row])
