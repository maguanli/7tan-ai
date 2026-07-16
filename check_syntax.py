"""检查 qq_bridge tools.py 语法"""
import ast

try:
    with open(r"D:\7tan\7tanAI\data\plugins\qq_bridge\tools.py", "r", encoding="utf-8") as f:
        source = f.read()
    ast.parse(source)
    print("✅ 语法检查通过！")
    print(f"  文件大小: {len(source)} 字符")
    print(f"  行数: {source.count(chr(10))} 行")
    
    # Check key elements
    checks = [
        ("register_tool导入", "register_tool = _import_register_tool()" in source),
        ("@register_tool装饰器", "@register_tool" in source),
        ("qq_connect函数", "def qq_connect" in source),
        ("qq_disconnect函数", "def qq_disconnect" in source),
        ("qq_send_message函数", "def qq_send_message" in source),
        ("qq_get_messages函数", "def qq_get_messages" in source),
        ("qq_status函数", "def qq_status" in source),
    ]
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")
        
except SyntaxError as e:
    print(f"❌ 语法错误: {e}")
except Exception as e:
    print(f"❌ 错误: {e}")
