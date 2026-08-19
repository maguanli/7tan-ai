"""清除 git 历史中 fix_doubao_key.py 的密钥"""
import subprocess, os, re

os.chdir("D:/7tan/7tanAI")

# 方法：用 git filter-branch 清除包含密钥的文件
# 先创建一个空的 fix_doubao_key.py（无密钥版本）
clean_content = '''"""临时修复豆包API Key变量名"""
import os
print("This script is deprecated. Keys are now managed via environment variables.")
'''

with open("scripts/fix_doubao_key_clean.py", "w", encoding="utf-8") as f:
    f.write(clean_content)

# 用 sed 替换模式：在 filter-branch 中将 fix_doubao_key.py 的内容替换为干净版本
cmd = (
    'set FILTER_BRANCH_SQUELCH_WARNING=1 && '
    'git filter-branch --force --tree-filter '
    '"python -c \"import os,sys; f=\'scripts/fix_doubao_key.py\'; '
    'c=open(f,\'r\',encoding=\'utf-8\',errors=\'ignore\').read() if os.path.exists(f) else \'\'; '
    'k=[l for l in c.split(chr(10)) if \'api_key\' in l.lower() or \'akv\' in l]; '
    'open(f,\'w\').write(\'# cleaned\\n\') if k and os.path.exists(f) else None\"" '
    '-- --all'
)
print("Running filter-branch...")
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
print("STDOUT:", result.stdout[-500:] if result.stdout else "(empty)")
print("STDERR:", result.stderr[-500:] if result.stderr else "(empty)")
print("RC:", result.returncode)

# 清理
os.remove("scripts/fix_doubao_key_clean.py")
