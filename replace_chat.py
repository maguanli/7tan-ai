#!/usr/bin/env python
"""Replace old ChatPage code with import from chat_page.py"""
import re

with open('src/ui/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_start = '# ===== Enter 发送输入框 ====='
old_end = '# ===== 资源管理页面（表格） ====='

start_idx = content.find(old_start)
end_idx = content.find(old_end)

if start_idx < 0 or end_idx < 0:
    print(f'ERROR: markers not found. start={start_idx}, end={end_idx}')
    import sys; sys.exit(1)

# Find the end of the line before the marker
end_of_old = content.rfind('\n', 0, end_idx - 1) + 1

print(f'Replacing from index {start_idx} to {end_of_old}')
print(f'Characters to remove: {end_of_old - start_idx}')

new_code = '''# ===== 导入重写的 ChatPage（from chat_page.py）=====
from .chat_page import ChatPage, MessageInput


'''

new_content = content[:start_idx] + new_code + content[end_of_old:]

with open('src/ui/app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f'Done! New file length: {len(new_content)} chars')
