# -*- coding: utf-8 -*-
import re, sys, io, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

p = r'D:\7tan\7tan_cn_20260515_090725.sql'
t0=time.time()
with open(p, 'r', encoding='utf-16', errors='ignore') as f:
    data = f.read()
print('read done', round(time.time()-t0,1),'s, chars', len(data))

def unescape_mysql(s):
    if s is None: return None
    if s=="NULL": return None
    if len(s)>=2 and s[0]=="'" and s[-1]=="'":
        s=s[1:-1]
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
            if c==',': vals.append(cur); cur=''; i+=1; continue
            cur+=c; i+=1; continue
    vals.append(cur)
    return vals

def parse_rows(table):
    rows=[]
    for m in re.finditer(r"INSERT INTO `"+re.escape(table)+r"` VALUES (.*?);\n", data, re.S):
        blob=m.group(1)
        i=0; n=len(blob)
        while i<n:
            if blob[i]!='(': i+=1; continue
            depth=0; q=False; j=i; cur=''
            while j<n:
                c=blob[j]
                if q:
                    if c=='\\': cur+=c+(blob[j+1] if j+1<n else ''); j+=2; continue
                    if c=="'":
                        if j+1<n and blob[j+1]=="'": cur+="''"; j+=2; continue
                        q=False; cur+=c; j+=1; continue
                    cur+=c; j+=1; continue
                else:
                    if c=="'": q=True; cur+=c; j+=1; continue
                    if c=='(': depth+=1; cur+=c if depth>1 else ''; j+=1; continue
                    if c==')':
                        depth-=1
                        if depth==0: j+=1; break
                        cur+=c; j+=1; continue
                    cur+=c; j+=1; continue
            rows.append([unescape_mysql(x) for x in split_fields(cur)])
            i=j
    return rows

# 用户表探测
for ut in ['users','username','admin','admins']:
    cnt = data.count("INSERT INTO `%s`"%ut)
    print('user-table insert count', ut, cnt)

for tbl in ['ll_lt','ll_lthf']:
    t1=time.time()
    rows=parse_rows(tbl)
    print(f'{tbl}: {len(rows)} rows parsed in {round(time.time()-t1,1)}s')
    # 保存
    with open(rf'D:\7tan\7tanAI\_{tbl}.json','w',encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False)
    print('saved', tbl)
