@echo off
chcp 65001 >nul
cd /d D:\7tan\7tanAI
git add -A
git commit -m "fix(p0): release v1.0.3 签名与净化 - 剔除auth_client_broken残留 统一online_verify修复版pyd 生成RSA签名 更新version.json"
git log --oneline -3
