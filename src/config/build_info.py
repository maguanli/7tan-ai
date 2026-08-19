"""
构建水印 — 基线版本（免费版）

此文件由 package_release.py / build_and_sync.bat 维护：
- 开发机构建的 exe 始终为 FREE（免费版水印）
- 专业源码包由 package_release.py 注入唯一 BUILD_ID（PRO-日期-时间-随机码）
- 专业用户用 rebuild.bat 自构建时，水印随源码编译进 exe，泄露可溯源
"""

BUILD_ID = "FREE"
BUILD_TIME = "2026-08-01 00:00:00"
BUILD_USER = ""
