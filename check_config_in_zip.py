# -*- coding: utf-8 -*-
"""从 zip 提取 config.yaml 检查是否含真实密钥"""
import zipfile, re, os

def extract_config(zip_path, member, out_path):
    z = zipfile.ZipFile(zip_path)
    try:
        data = z.read(member)
    except KeyError:
        print(f"[{os.path.basename(zip_path)}] 未找到 {member}")
        return None
    text = data.decode('utf-8', errors='replace')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"[{os.path.basename(zip_path)}] 已提取 {member} -> {out_path} ({len(text)} 字符)")
    return text

if __name__ == '__main__':
    base = r'D:\7tan\7tanAI\dist\release\github'
    # 1) web 版
    t1 = extract_config(os.path.join(base, '7tan-web-v1.0.13.zip'), 'config/config.yaml', r'D:\7tan\7tanAI\check_web_config.yaml')
    # 2) editor free 版
    t2 = extract_config(os.path.join(base, '7tan-editor-free-v1.0.13.zip'), '7tan-editor/_internal/config/config.yaml', r'D:\7tan\7tanAI\check_editor_config.yaml')
    for name, text in [('web', t1), ('editor', t2)]:
        if text is None:
            continue
        print(f"\n===== {name} config.yaml 中敏感字段扫描 =====")
        # 找 api_key / secret / token / password 等
        for line in text.splitlines():
            if re.search(r'(api_key|api-key|secret|token|password|passwd|access_key|access-key|private)', line, re.I):
                # 脱敏显示：只显示 key 名和前几位
                m = re.match(r'\s*([^:]+):\s*(.+)', line)
                if m:
                    k = m.group(1).strip()
                    v = m.group(2).strip()
                    if v and v not in ('""', "''", 'null', 'None', ''):
                        # 脱敏
                        v_masked = v[:8] + '***' if len(v) > 8 else v
                        print(f"  {k} = {v_masked}")
