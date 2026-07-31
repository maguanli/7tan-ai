import shutil
# 修复版 rebuild.bat 同步到源码根目录（覆盖旧版 7tan-updater 残留）
src = r"D:\7tan\7tanAI\dist\rebuild.bat"
dst = r"D:\7tan\7tanAI\rebuild.bat"
shutil.copy2(src, dst)
print("COPIED-TO-ROOT", dst)
