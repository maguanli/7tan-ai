# 修复 browser_tools.py 中的 _web_view bug
with open('src/tools/browser_tools.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 统计替换前
count_before = content.count('_web_view')
print(f"替换前: {count_before} 处 _web_view")

# 执行替换
content = content.replace('if _web_view is not None:', 'if _get_active_view() is not None:')
content = content.replace('if _web_view is None:', 'if _get_active_view() is None:')

# 统计替换后
count_after = content.count('_web_view')
print(f"替换后: {count_after} 处 _web_view")

# 写回文件
with open('src/tools/browser_tools.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 修复完成！")
