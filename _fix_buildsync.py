# -*- coding: utf-8 -*-
"""给 build_and_sync.bat 增加 PYZ.pyz 校验"""
p = r"D:\7tan\7tanAI\build_and_sync.bat"
with open(p, "r", encoding="utf-8") as f:
    content = f.read()

# 在 8/8 pyd 校验之前加入 PYZ 检查
anchor = 'if not exist "dist\\7tan-editor\\_internal\\src\\security\\rsa_verify.pyd" set PYD_OK=0'
add = '''if not exist "dist\\7tan-editor\\_internal\\PYZ.pyz" (
    echo [错误] 产物缺少 PYZ.pyz，构建不完整！可能被杀毒软件拦截
    echo 请将 dist 目录加入杀毒白名单后重新构建
    pause
    exit /b 1
)
echo [OK] PYZ.pyz 已生成
'''
if "PYZ.pyz 已生成" in content:
    print("已存在，跳过")
elif anchor in content:
    content = content.replace(anchor, add + anchor)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: build_and_sync.bat 已加入 PYZ 校验")
else:
    print("WARN: 未找到锚点")
